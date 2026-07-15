; OBS多视角切换器 Inno Setup 安装脚本
; 使用方法: 安装 Inno Setup 后, 双击此文件或用 ISCC.exe 编译

#define MyAppName "OBS多视角切换器"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "创作者"
#define MyAppExeName "OBS多视角切换器.exe"
#define MyAppIconName "OBS多视角切换器.lnk"

[Setup]
; 基本设置
AppId={{B8D9F3E2-1A4C-4D5E-9F2A-7C8D6E5B4A3F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (c) 2026 创作者. 保留所有权利.
LicenseFile=LICENSE.txt
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=OBS多视角切换器_安装包_v1.0.0
SetupIconFile=app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; 界面语言 (使用本地中文语言文件)
[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

; 安装的任务选项 (桌面快捷方式)
[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加任务:"

; 要打包的文件 (PyInstaller 生成的整个目录)
[Files]
; 主程序 exe
Source: "dist\OBS多视角切换器\OBS多视角切换器.exe"; DestDir: "{app}"; Flags: ignoreversion
; _internal 完整目录 (所有依赖库和数据文件)
Source: "dist\OBS多视角切换器\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; 配置文件和媒体工具 (放根目录, 用户可修改)
Source: "mediamtx.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; VLC 静默安装包 (安装时检测,未装则静默安装)
Source: "vlc-setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall nocompression
; LICENSE 文件
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
; 使用说明
Source: "使用说明.txt"; DestDir: "{app}"; Flags: ignoreversion

; 创建快捷方式
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.txt"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

; 安装后运行
[Run]
; VLC 静默安装: 检测未装则安装 (/S 静默模式, /D 指定目录)
Filename: "{tmp}\vlc-setup.exe"; Parameters: "/S"; StatusMsg: "正在安装 VLC 播放器 (Twitch源与监视器预览需要)..."; Check: NeedInstallVLC(); Flags: waituntilterminated
; 启动主程序
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

; 卸载时删除用户数据 (APPDATA 中的配置/日志/mediamtx.yml)
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\OBS多视角切换器"

[Code]
const
  WM_CLOSE = $0010;

// 检测系统是否已安装 VLC (通过注册表)
// 检查 HKLM 64位和32位两个位置
function NeedInstallVLC(): Boolean;
var
  vlcPath: String;
begin
  // 优先检查 64 位注册表
  if RegQueryStringValue(HKLM, 'SOFTWARE\VideoLAN\VLC', 'InstallDir', vlcPath) then begin
    Result := False;
    Exit;
  end;
  // 检查 32 位注册表 (WOW6432Node)
  if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\VideoLAN\VLC', 'InstallDir', vlcPath) then begin
    Result := False;
    Exit;
  end;
  // 检查当前用户
  if RegQueryStringValue(HKCU, 'SOFTWARE\VideoLAN\VLC', 'InstallDir', vlcPath) then begin
    Result := False;
    Exit;
  end;
  // 未找到 VLC,需要安装
  Result := True;
end;

// 检测并关闭正在运行的主程序 (覆盖安装时旧版本可能正在运行, 导致 exe 被锁定无法覆盖)
// 返回 True 表示已关闭或未运行, 可以继续安装; False 表示用户取消
function InitializeSetup(): Boolean;
var
  hWnd: HWND;
  retryCount: Integer;
begin
  retryCount := 0;
  while retryCount < 3 do begin
    hWnd := FindWindowByWindowName('OBS多视角切换器');
    if hWnd = 0 then begin
      // 主窗口未找到, 可能未运行, 继续安装
      Result := True;
      Exit;
    end;
    // 询问用户是否关闭 (首次提示, 后续静默强制关闭)
    if retryCount = 0 then begin
      if MsgBox('检测到 OBS多视角切换器 正在运行, 需要关闭它才能继续安装。是否立即关闭?',
                 mbConfirmation, MB_YESNO) = IDNO then begin
        Result := False;
        Exit;
      end;
    end;
    // 发送关闭消息
    PostMessage(hWnd, WM_CLOSE, 0, 0);
    // 等待进程退出
    Sleep(1500);
    // 再次检查是否仍在运行 (通过进程名)
    if hWnd = FindWindowByWindowName('OBS多视角切换器') then begin
      // 窗口仍在, 尝试用 taskkill 强制结束
      Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM "{#MyAppExeName}"',
           '', SW_HIDE, ewWaitUntilTerminated, retryCount);
      Sleep(1000);
    end;
    // 最终检查
    if FindWindowByWindowName('OBS多视角切换器') = 0 then begin
      Result := True;
      Exit;
    end;
    retryCount := retryCount + 1;
  end;
  // 3 次尝试后仍在运行, 报错退出
  MsgBox('无法关闭正在运行的 OBS多视角切换器, 请手动关闭后重试。',
         mbError, MB_OK);
  Result := False;
end;

// 卸载前同样检测并关闭运行中的主程序
function InitializeUninstall(): Boolean;
var
  hWnd: HWND;
  resultCode: Integer;
begin
  hWnd := FindWindowByWindowName('OBS多视角切换器');
  if hWnd <> 0 then begin
    PostMessage(hWnd, WM_CLOSE, 0, 0);
    Sleep(1500);
    if FindWindowByWindowName('OBS多视角切换器') <> 0 then begin
      Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM "{#MyAppExeName}"',
           '', SW_HIDE, ewWaitUntilTerminated, resultCode);
      Sleep(1000);
    end;
  end;
  Result := True;
end;
