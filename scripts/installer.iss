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
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Antigravity-Orbit
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
Source: "..\dist\Antigravity-Orbit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config.example.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdestfiledoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\config.json"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\*.json"
Type: filesandordirs; Name: "{app}\*.txt"
Type: dirifempty; Name: "{app}"
