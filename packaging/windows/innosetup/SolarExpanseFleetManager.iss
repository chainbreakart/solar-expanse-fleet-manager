#define MyAppName "Solar Expanse Fleet Manager"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Solar Expanse Tools"
#define MyAppExeName "SolarExpanseFleetManager.exe"

[Setup]
AppId={{E9D7D641-8998-48D2-8DFB-7F8BB3D410E0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\..\dist\installer
OutputBaseFilename=SolarExpanseFleetManager-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\..\dist\SolarExpanseFleetManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{localappdata}\SolarExpanseFleetManager"
Name: "{localappdata}\SolarExpanseFleetManager\logs"
Name: "{localappdata}\SolarExpanseFleetManager\ipc"
Name: "{localappdata}\SolarExpanseFleetManager\cache"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
