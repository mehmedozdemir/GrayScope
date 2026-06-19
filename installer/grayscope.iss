; GrayScope Windows Installer — Inno Setup 6
; Build: ISCC installer\grayscope.iss
; Requires the PyInstaller output at dist\GrayScope\

#define AppName      "GrayScope"
#define AppVersion   "0.1.0"
#define AppPublisher "GrayScope"
#define AppExeName   "GrayScope.exe"
#define AppURL       "https://github.com/your-org/grayscope"

[Setup]
AppId={{E7C4B2F1-3A8D-4E9F-B5C6-1D2E7A3F9B0C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Single-user install by default (no UAC required)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer\output
OutputBaseFilename=GrayScope-{#AppVersion}-Setup
SetupIconFile=..\assets\grayscope.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Windows 10/11 minimum
MinVersion=10.0.17763
; Show a nice banner colour
WizardImageFile=compiler:WizModernImage.bmp
WizardSmallImageFile=compiler:WizModernSmallImage.bmp
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "turkish";  MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english";  MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Windows başlangıcında otomatik başlat"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application bundle (PyInstaller one-folder output)
Source: "..\dist\GrayScope\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName}'i Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Optional auto-start entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the user-data folder on uninstall only if the user confirms
; (the app stores its DB under %APPDATA%\GrayScope — we leave that alone
;  so settings survive a reinstall; user can delete manually if desired)

[Code]
// No custom code needed for basic install.
