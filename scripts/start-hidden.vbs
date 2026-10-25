' Englearn 开机自启入口：静默启动，不弹控制台，登录后自动打开页面。
' 由「设置 → 开机自动启动」写入注册表，不需要手动运行本文件。
Option Explicit

Dim sh, fso, base, target, logsDir
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 本文件在 <项目>\scripts\ 下，往上一层就是项目根目录
base = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
target = base & "\start.cmd"

If Not fso.FileExists(target) Then
    WScript.Quit 1
End If

' 运行日志落在 logs\server.log，出问题先看这里
logsDir = base & "\logs"
If Not fso.FolderExists(logsDir) Then fso.CreateFolder(logsDir)

sh.CurrentDirectory = base
' 0 = 隐藏窗口，False = 不等待；输出重定向避免隐藏控制台下的写入问题
' --silent：出错时不挂起等待按键；不给 --no-open，启动后会自动打开页面
sh.Run "cmd.exe /c start.cmd --silent >> logs\server.log 2>&1", 0, False
