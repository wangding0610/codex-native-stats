"""Rollback, path ownership and actual shortcut/registry integration checks."""
from pathlib import Path
from unittest.mock import patch
import importlib.util, json, os, shutil, types, unittest, uuid, winreg

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stats_installer', ROOT/'installer/install.py')
install = importlib.util.module_from_spec(spec);spec.loader.exec_module(install)

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT/'validation'/('unit-'+uuid.uuid4().hex)
        self.base.mkdir(parents=True)

    def tearDown(self):
        install.remove_child(ROOT/'validation', self.base)

    def test_traversal_is_rejected(self):
        for file in [self.base, self.base/'../outside', ROOT/'VERSION']:
            with self.assertRaises(ValueError): install.safe_child(self.base,file)

    def test_disabled_legacy_plugin_must_be_removed_before_migration(self):
        home=self.base/'home';home.mkdir()
        before=b'[plugins."codex-native-stats@personal"]\nenabled=false\n'
        (home/'config.toml').write_bytes(before)
        command=types.SimpleNamespace(root=str(self.base/'install'),payload=str(ROOT/'build/payload'),
            codex_home=str(home),cli=None,isolated=True)
        with patch.object(install,'find_cli',return_value='dummy'):
            with self.assertRaisesRegex(RuntimeError,'personal'):install.install(command)
        self.assertEqual((home/'config.toml').read_bytes(),before)

    def test_cli_failure_rolls_back_config_and_staged_payload(self):
        home=self.base/'home';home.mkdir()
        before=b'model="unrelated"\n'
        (home/'config.toml').write_bytes(before)
        root=self.base/'install'
        command=types.SimpleNamespace(root=str(root),payload=str(ROOT/'build/payload'),
            codex_home=str(home),cli=None,isolated=True)
        def fake_cli(exe, target, *args):
            if args[0]=='marketplace':
                (target/'config.toml').write_text('model="unrelated"\n[marketplaces.codex-stats]\nsource="fake"\n')
                return '{}'
            raise RuntimeError('simulated plugin install failure')
        with patch.object(install,'find_cli',return_value='dummy'),patch.object(install,'cli',side_effect=fake_cli):
            with self.assertRaisesRegex(RuntimeError,'simulated'): install.install(command)
        self.assertEqual((home/'config.toml').read_bytes(),before)
        self.assertFalse((root/'install.json').exists())
        self.assertFalse(any((root/'versions').iterdir()))

    def test_real_shortcuts_and_registry_use_only_owned_locations(self):
        import win32com.client
        real=win32com.client.Dispatch('WScript.Shell')
        original_dispatch=win32com.client.Dispatch
        desktop=self.base/'desktop';desktop.mkdir()
        programs=self.base/'programs';programs.mkdir()
        class Shell:
            def SpecialFolders(self,name): return str(desktop if name=='Desktop' else programs)
            def CreateShortcut(self,file): return real.CreateShortcut(file)
        key=r'Software\CodexStatsValidation-'+uuid.uuid4().hex
        uninstall=key+'-uninstall'
        def dispatch(value,*args,**kwargs):
            return Shell() if isinstance(value,str) and value=='WScript.Shell' else original_dispatch(value,*args,**kwargs)
        try:
            with patch.object(win32com.client,'Dispatch',side_effect=dispatch),patch.object(install,'REGISTRY',key),patch.object(install,'UNINSTALL',uninstall):
                links=install.integrations(self.base,'3.0.0',self.base/'home')
            self.assertEqual(len(links),3)
            for file in links:
                link=real.CreateShortcut(file)
                self.assertEqual(Path(link.TargetPath),self.base/'CodexStats.exe')
                self.assertIn(link.Arguments,['--launch','--uninstall'])
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key) as handle:
                self.assertEqual(winreg.QueryValueEx(handle,'InstallRoot')[0],str(self.base))
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,uninstall) as handle:
                self.assertEqual(winreg.QueryValueEx(handle,'DisplayVersion')[0],'3.0.0')
        finally:
            for path in [key,uninstall]:
                try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)
                except FileNotFoundError:pass

if __name__=='__main__':unittest.main(verbosity=2)
