using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Microsoft.Win32;
using System.Windows.Forms;

// Only a process launcher: MCP stdin/stdout are copied as bytes, without translation.
class Host {
    static void Pump(Stream input, Stream output) {
        byte[] buffer = new byte[4096]; int count;
        while ((count = input.Read(buffer, 0, buffer.Length)) > 0) {
            output.Write(buffer, 0, count); output.Flush();
        }
    }
    static string Quote(string value) {
        string escaped = Regex.Replace(value, "(\\\\*)\"", "$1$1\\\"");
        return "\"" + Regex.Replace(escaped, @"(\\+)$", "$1$1") + "\"";
    }
    static int Main(string[] args) {
        try {
            string root = Environment.GetEnvironmentVariable("CODEX_STATS_INSTALL_ROOT");
            if (String.IsNullOrEmpty(root)) {
                using (var key = Registry.CurrentUser.OpenSubKey(@"Software\CodexNativeStats"))
                    root = key == null ? null : key.GetValue("InstallRoot") as string;
            }
            if (String.IsNullOrEmpty(root)) root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "CodexNativeStats");
            string version = File.ReadAllText(Path.Combine(root, "current-version.txt")).Trim();
            if (!Regex.IsMatch(version, @"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$")) throw new Exception("Invalid runtime version.");
            string active = Path.Combine(root, "versions", version);
            string mode = args.Length == 0 ? "--server" : args[0];
            string script;
            if (mode == "--launch") script = Path.Combine(active, @"marketplace\plugins\codex-native-stats\runtime\launch_official.py");
            else if (mode == "--uninstall") script = Path.Combine(active, @"installer\install.py");
            else if (mode == "--server") script = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), @"..\plugin_server.py"));
            else throw new Exception("Unknown launcher mode.");
            var start = new ProcessStartInfo(Path.Combine(active, @"python\python.exe"), Quote(script) +
                (mode == "--uninstall" ? " uninstall --root " + Quote(root) : ""));
            start.UseShellExecute = false; start.CreateNoWindow = true;
            start.RedirectStandardInput = true; start.RedirectStandardOutput = true;
            start.RedirectStandardError = true;
            start.WorkingDirectory = Path.GetDirectoryName(script);
            start.EnvironmentVariables["CODEX_STATS_NODE"] = Path.Combine(active, @"node\node.exe");
            start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            using (var child = Process.Start(start)) {
                Task input = Task.Factory.StartNew(() => {
                    try { Pump(Console.OpenStandardInput(),child.StandardInput.BaseStream); }
                    catch (IOException) {} finally { try { child.StandardInput.Close(); } catch {} }
                });
                Task output = Task.Factory.StartNew(() => Pump(child.StandardOutput.BaseStream,Console.OpenStandardOutput()));
                Task error = Task.Factory.StartNew(() => Pump(child.StandardError.BaseStream,Console.OpenStandardError()));
                child.WaitForExit(); Task.WaitAll(output, error); return child.ExitCode;
            }
        } catch (Exception e) {
            string error = "Codex Stats: " + e.Message + " Install or repair the Windows package from https://github.com/wangding0610/codex-native-stats/releases";
            if (args.Length > 0 && args[0] != "--server") MessageBox.Show(error, "Codex 输入栏统计", MessageBoxButtons.OK, MessageBoxIcon.Error);
            else Console.Error.WriteLine(error);
            return 1;
        }
    }
}
