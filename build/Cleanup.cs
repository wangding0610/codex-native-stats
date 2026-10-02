using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

// Delayed cleanup with an ownership marker and exactly two allowed targets.
class Cleanup {
    static int Main(string[] args) {
        if (args.Length != 2) return 2;
        string root = Path.GetFullPath(args[0]).TrimEnd(Path.DirectorySeparatorChar);
        string marker = Path.Combine(root, "uninstall-pending.txt");
        try {
            if (root == Path.GetPathRoot(root).TrimEnd(Path.DirectorySeparatorChar)) return 2;
            if (!File.Exists(marker) || File.ReadAllText(marker).Replace("\r\n","\n") != "CodexNativeStats\n" + root) return 2;
            if ((File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0) return 2;
            int pid;
            if (Int32.TryParse(args[1], out pid)) {
                try { using (var parent = Process.GetProcessById(pid)) parent.WaitForExit(10000); } catch (ArgumentException) {}
            }
            for (int attempt = 0; attempt < 40; attempt++) {
                try {
                    string versions = Path.Combine(root, "versions");
                    string launcher = Path.Combine(root, "CodexStats.exe");
                    if (Directory.Exists(versions)) Directory.Delete(versions, true);
                    if (File.Exists(launcher)) File.Delete(launcher);
                    File.Delete(marker);
                    if (Directory.GetFileSystemEntries(root).Length == 0) Directory.Delete(root);
                    return 0;
                } catch (IOException) { Thread.Sleep(500); }
                catch (UnauthorizedAccessException) { Thread.Sleep(500); }
            }
            File.WriteAllText(Path.Combine(root,"cleanup-error.txt"), "Windows still has an installed file open. Close the statistics launcher and retry cleanup.");
            return 1;
        } catch (Exception error) {
            try { File.WriteAllText(Path.Combine(root,"cleanup-error.txt"),error.ToString()); } catch {}
            return 1;
        }
    }
}
