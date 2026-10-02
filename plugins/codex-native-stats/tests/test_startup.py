"""Delayed startup and cancellation checks, without touching the official App."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import official_adapter as adapter

class StartupTests(unittest.TestCase):
    def test_store_install_on_another_drive(self):
        root=r'D:\WindowsApps\OpenAI.Codex_26.930.2377.0_x64__2p2nqsd0c76g0'
        with patch.object(adapter.subprocess,'run',return_value=MagicMock(stdout=root)),patch.object(Path,'is_file',return_value=True):
            self.assertEqual(adapter.installed_app(),Path(root)/'app/ChatGPT.exe')

    def wait(self,ports,alive=True,registered=True,cancel=False):
        state=MagicMock();state.__truediv__.return_value.exists.return_value=cancel
        with patch.object(adapter,'STATE',state),patch.object(adapter,'status') as status,patch.object(adapter,'enabled',return_value=True),patch.object(adapter,'registered',return_value=registered),patch.object(adapter,'official_pids',return_value=[10] if alive else []),patch.object(adapter,'debug_port',side_effect=ports) as debug,patch.object(adapter,'fresh_debug_port',return_value=None),patch.object(adapter.time,'sleep') as sleep:
            result=adapter.wait_for_renderer()
        return result,status,debug,sleep

    def test_endpoint_ready_after_old_timeout(self):
        result,status,debug,sleep=self.wait([None]*100+[51933])
        self.assertEqual(result,51933)
        self.assertEqual(sleep.call_count,100)
        self.assertEqual(sum(c.args[0] for c in sleep.call_args_list),50)
        self.assertEqual(debug.call_count,101)
        self.assertEqual(status.call_args_list[0].args[0],'waiting_for_renderer')

    def test_app_closed(self):
        result,status,debug,sleep=self.wait([],alive=False)
        self.assertIsNone(result);debug.assert_not_called();sleep.assert_not_called()
        self.assertEqual(status.call_args.kwargs['reason'],'official-app-closed-before-renderer-ready')

    def test_plugin_removed(self):
        result,status,debug,_=self.wait([],registered=False)
        self.assertIsNone(result);debug.assert_not_called()
        self.assertEqual(status.call_args.kwargs['reason'],'plugin-uninstalled')

    def test_cancel_requested(self):
        result,status,debug,_=self.wait([],cancel=True)
        self.assertIsNone(result);debug.assert_not_called()
        self.assertEqual(status.call_args.args[0],'cancelled')

    def test_only_official_profile_with_endpoint_is_eligible(self):
        official=r'C:\Program Files\WindowsApps\OpenAI.Codex_26.928.3736.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe'
        good={'name':'ChatGPT.exe','exe':official,'cmdline':['--user-data-dir='+str(adapter.BROWSER),'--remote-debugging-port=0']}
        for args,expected in [(good['cmdline'],True),([],False),(good['cmdline']+['--type=renderer'],False),(['--user-data-dir=other','--remote-debugging-port=0'],False)]:
            process=MagicMock();process.info={**good,'cmdline':args}
            with patch.object(adapter.psutil,'process_iter',return_value=[process]):self.assertEqual(adapter.official_debug_requested(),expected)
        process=MagicMock();process.info={**good,'exe':r'E:\other\ChatGPT.exe'}
        with patch.object(adapter.psutil,'process_iter',return_value=[process]):self.assertFalse(adapter.official_debug_requested())

    def test_stalled_primary_probe_recovers_without_restarting_app(self):
        state=MagicMock();state.__truediv__.return_value.exists.return_value=False
        clock=iter([0,0,1,2,3,4,5,5])
        with patch.object(adapter,'STATE',state),patch.object(adapter,'status') as status,patch.object(adapter,'enabled',return_value=True),patch.object(adapter,'registered',return_value=True),patch.object(adapter,'official_pids',return_value=[10]),patch.object(adapter,'debug_port',return_value=None),patch.object(adapter,'fresh_debug_port',return_value=51933) as fresh,patch.object(adapter.time,'sleep'),patch.object(adapter.time,'monotonic',side_effect=clock),patch.object(adapter,'start_official') as start:
            self.assertEqual(adapter.wait_for_renderer(),51933)
        fresh.assert_called_once();start.assert_not_called()
        self.assertTrue(status.call_args.kwargs['recoveredByFreshProbe'])

    def test_malformed_fresh_probe_is_rejected(self):
        for stdout in ['{}','{"port":false,"diagnostic":{"reason":"ready"}}','{"port":51933,"diagnostic":{"reason":"listener-profile-mismatch"}}','{"port":70000,"diagnostic":{"reason":"ready"}}']:
            with patch.object(adapter.subprocess,'run',return_value=MagicMock(stdout=stdout)):
                self.assertIsNone(adapter.fresh_debug_port())

    def test_package_cache_mapping_and_isolated_profile(self):
        files=adapter.endpoint_port_files(adapter.BROWSER)
        self.assertEqual(files[0],adapter.BROWSER/'DevToolsActivePort')
        self.assertEqual(files[1],Path.home()/'AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Roaming/Codex/web/Codex/DevToolsActivePort')
        isolated=Path(r'D:\isolated\browser')
        self.assertEqual(adapter.endpoint_port_files(isolated),[isolated/'DevToolsActivePort'])

    def test_desktop_reads_package_port_when_logical_file_missing(self):
        files=adapter.endpoint_port_files(adapter.BROWSER)
        def read(file,*args,**kwargs):
            if file==files[0]:raise FileNotFoundError
            return '51933\n'
        connection=MagicMock(status='LISTEN',pid=10);connection.laddr.port=51933;connection.laddr.ip='127.0.0.1'
        process=MagicMock(pid=10);process.exe.return_value=r'C:\Program Files\WindowsApps\OpenAI.Codex_26.928.3736.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe';process.cmdline.return_value=['--user-data-dir='+str(adapter.BROWSER),'--remote-debugging-port=0']
        with patch.object(Path,'read_text',autospec=True,side_effect=read),patch.object(adapter.psutil,'net_connections',return_value=[connection]),patch.object(adapter.psutil,'Process',return_value=process):
            self.assertEqual(adapter.debug_port(),51933)
        self.assertEqual(adapter._endpoint_diagnostic['portFile'],str(files[1]))

    def test_package_file_does_not_bypass_owner_validation(self):
        files=adapter.endpoint_port_files(adapter.BROWSER)
        def read(file,*args,**kwargs):
            if file==files[0]:raise FileNotFoundError
            return '51933\n'
        connection=MagicMock(status='LISTEN',pid=10);connection.laddr.port=51933;connection.laddr.ip='127.0.0.1'
        process=MagicMock(pid=10);process.exe.return_value=r'E:\other\ChatGPT.exe'
        with patch.object(Path,'read_text',autospec=True,side_effect=read),patch.object(adapter.psutil,'net_connections',return_value=[connection]),patch.object(adapter.psutil,'Process',return_value=process):
            self.assertIsNone(adapter.debug_port())
        self.assertEqual(adapter._endpoint_diagnostic['reason'],'unexpected-listener-owner')

    def test_stale_logical_port_does_not_hide_valid_package_port(self):
        files=adapter.endpoint_port_files(adapter.BROWSER)
        def read(file,*args,**kwargs):return '51932\n' if file==files[0] else '51933\n'
        connection=MagicMock(status='LISTEN',pid=10);connection.laddr.port=51933;connection.laddr.ip='127.0.0.1'
        process=MagicMock(pid=10);process.exe.return_value=r'C:\Program Files\WindowsApps\OpenAI.Codex_26.928.3736.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe';process.cmdline.return_value=['--user-data-dir='+str(adapter.BROWSER),'--remote-debugging-port=0']
        with patch.object(Path,'read_text',autospec=True,side_effect=read),patch.object(adapter.psutil,'net_connections',return_value=[connection]),patch.object(adapter.psutil,'Process',return_value=process):
            self.assertEqual(adapter.debug_port(),51933)

if __name__=='__main__':unittest.main(verbosity=2)
