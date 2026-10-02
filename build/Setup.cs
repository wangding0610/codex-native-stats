using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Windows.Forms;

class Setup {
    static string Quote(string value) {
        string escaped = Regex.Replace(value, "(\\\\*)\"", "$1$1\\\"");
        return "\"" + Regex.Replace(escaped, @"(\\+)$", "$1$1") + "\"";
    }
    [STAThread]
    static int Main(string[] args) {
        bool silent = Array.IndexOf(args, "--silent") >= 0;
        string temp = Path.Combine(Path.GetTempPath(), "CodexStatsSetup-" + Guid.NewGuid().ToString("N"));
        try {
            if (!Environment.Is64BitOperatingSystem) throw new Exception("Windows x64 is required.");
            if (!silent && MessageBox.Show("安装 Codex 输入栏统计 3.0.2？\n\n适用于 Windows x64 微软商店版 Codex，包含运行环境，无需管理员权限。\n请先保存任务，安装后用“Codex 官方版（输入栏统计）”启动。\n\n项目按 MIT 协议开源。", "Codex 输入栏统计", MessageBoxButtons.OKCancel, MessageBoxIcon.Information) != DialogResult.OK) return 2;
            Directory.CreateDirectory(temp);
            string zip = Path.Combine(temp, "payload.zip");
            using (var input = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (var output = File.Create(zip)) input.CopyTo(output);
            string payload = Path.Combine(temp, "payload");
            ZipFile.ExtractToDirectory(zip, payload);
            string command = Quote(Path.Combine(payload, @"installer\install.py")) + " install --payload " + Quote(payload);
            foreach (string arg in args) if (arg != "--silent") command += " " + Quote(arg);
            var start = new ProcessStartInfo(Path.Combine(payload, @"python\python.exe"), command);
            start.UseShellExecute = false; start.CreateNoWindow = true;
            start.RedirectStandardOutput = true; start.RedirectStandardError = true;
            start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            using (var child = Process.Start(start)) {
                var stderr = child.StandardError.ReadToEndAsync();
                string output = child.StandardOutput.ReadToEnd(); child.WaitForExit();
                if (child.ExitCode != 0) throw new Exception(output + stderr.Result);
                if (!silent) MessageBox.Show("安装完成。\n\n请正常退出 Codex 一次，再使用桌面的“Codex 官方版（输入栏统计）”启动。\n在 设置 → 插件 中可开关“Codex 输入栏统计”。\n卸载入口在 Windows 设置 → 应用。", "Codex 输入栏统计", MessageBoxButtons.OK, MessageBoxIcon.Information);
                else Console.WriteLine(output);
                return 0;
            }
        } catch (Exception e) {
            if (!silent) MessageBox.Show(e.Message, "安装未完成", MessageBoxButtons.OK, MessageBoxIcon.Error);
            else Console.Error.WriteLine(e.Message);
            return 1;
        } finally {
            // The unique directory created above is the only recursive cleanup target.
            try { if (Directory.Exists(temp)) Directory.Delete(temp, true); } catch {}
        }
    }
}
