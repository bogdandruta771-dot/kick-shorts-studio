using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Program
{
    static void Log(string msg)
    {
        try
        {
            string logFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "launcher.log");
            File.AppendAllText(logFile, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + msg + Environment.NewLine);
        }
        catch { }
    }

    [STAThread]
    static void Main(string[] args)
    {
        try
        {
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            Log("OmniStudio launcher starting. BaseDirectory: " + appDir);
            string scriptPath = Path.Combine(appDir, "desktop_app.py");

            if (!File.Exists(scriptPath))
            {
                Log("Error: desktop_app.py not found at " + scriptPath);
                MessageBox.Show("Could not find desktop_app.py in: " + appDir, "OmniStudio Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            string pythonPath = "";
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] searchPaths = new string[]
            {
                Path.Combine(localApp, "Python", "pythoncore-3.14-64", "python.exe"),
                Path.Combine(localApp, "Python", "pythoncore-3.14-64", "pythonw.exe"),
                Path.Combine(localApp, "Programs", "Python", "Python314", "python.exe"),
                Path.Combine(localApp, "Programs", "Python", "Python314", "pythonw.exe"),
                "python.exe",
                "pythonw.exe"
            };

            foreach (string p in searchPaths)
            {
                if (File.Exists(p))
                {
                    pythonPath = p;
                    break;
                }
            }

            if (string.IsNullOrEmpty(pythonPath))
            {
                pythonPath = "python.exe";
            }

            Log("Resolved Python: " + pythonPath);
            string extraArgs = args.Length > 0 ? " " + string.Join(" ", args) : "";
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pythonPath;
            psi.Arguments = "\"" + scriptPath + "\"" + extraArgs;
            psi.WorkingDirectory = appDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;

            Log("Starting process: " + psi.FileName + " " + psi.Arguments);
            Process proc = Process.Start(psi);
            if (proc == null)
            {
                Log("Warning: Process.Start returned null");
                MessageBox.Show("Failed to launch OmniStudio.", "OmniStudio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            else
            {
                Log("Successfully spawned OmniStudio backend with PID " + proc.Id);
            }
        }
        catch (Exception ex)
        {
            Log("Fatal Exception: " + ex.ToString());
            MessageBox.Show("Failed to start OmniStudio: " + ex.Message, "OmniStudio Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
