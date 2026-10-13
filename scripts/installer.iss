; Inno Setup Script for Antigravity Orbit
; PrivilegesRequired=lowest ensures smooth user-level install without admin UAC popups

#define MyAppName "Antigravity Orbit"
#define MyAppVersion "3.3.20"
#define MyAppPublisher "Antigravity Team"
#define MyAppURL "https://github.com/akasls/Antigravity-Orbit"
#define MyAppExeName "Antigravity-Orbit.exe"

[Setup]
AppId={{C8F8A77E-6564-42DF-A62E-0C4D9A0BC7E1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Antigravity-Orbit
UsePreviousAppDir=yes
DisableDirPage=no
DisableProgramGroupPage=no
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=Antigravity-Orbit-Setup
SetupIconFile=..\resources\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
CloseApplicationsFilter=Antigravity-Orbit.exe
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Antigravity-Orbit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config.json,*.log"
Source: "..\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config.example.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Registry]
Root: HKCU; Subkey: "Software\AntigravityOrbit"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"; Flags: uninsdeletekeyifempty
Root: HKCU; Subkey: "Software\AntigravityOrbit"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekeyifempty
Root: HKCU; Subkey: "Software\AntigravityOrbit"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekeyifempty


[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\*.log"
Type: dirifempty; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  // 安装前强制关闭正在运行的 Orbit（包含后台与托盘常驻），防止文件锁死导致升级覆盖失败
  Exec('taskkill.exe', '/F /IM Antigravity-Orbit.exe /IM Antigravity-Orbit-Portable-x64.exe', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // 安装文件前清理 WebView2 静态磁盘缓存，确保不会加载旧版 HTML/CSS/JS 缓存
    DelTree(ExpandConstant('{userappdata}\Antigravity-Orbit\webview_cache\EBWebView\Default\Cache'), True, True, True);
    DelTree(ExpandConstant('{userappdata}\Antigravity-Orbit\webview_cache\EBWebView\Default\Code Cache'), True, True, True);
  end;
end;

