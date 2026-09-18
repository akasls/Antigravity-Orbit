; Inno Setup Script for Antigravity Orbit
; PrivilegesRequired=lowest ensures smooth user-level install without admin UAC popups

#define MyAppName "Antigravity Orbit"
#define MyAppVersion "3.3.3"
#define MyAppPublisher "Antigravity Team"
#define MyAppURL "https://github.com/akasls/Antigravity-Orbit"
#define MyAppExeName "Antigravity-Orbit.exe"

[Setup]
AppId={{C8F8A77E-6564-42DF-A62E-0C4D9A0BC7E1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Antigravity-Orbit
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=Antigravity-Orbit-Setup
SetupIconFile=..\resources\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Antigravity-Orbit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
