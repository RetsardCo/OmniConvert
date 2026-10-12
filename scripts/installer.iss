; OmniConvert Inno Setup Script
#define MyAppName "OmniConvert"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "OmniConvert Team"
#define MyAppURL "https://github.com/Kurados/OmniConvert"
#define MyAppExeName "OmniConvert.exe"

[Setup]
AppId={{D37E5528-912A-4B2D-9381-69FF28A5B3E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\releases
OutputBaseFilename=OmniConvert-Setup
SetupIconFile=..\src\omniconvert\resources\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full Installation (Includes OCR Engine and Whisper AI Model)"
Name: "compact"; Description: "Lite Installation (Core 70+ Formats Only)"
Name: "custom"; Description: "Custom Installation"; Flags: iscustom

[Components]
Name: "core"; Description: "OmniConvert Core Application (70+ Offline Formats: PDF, Word, Excel, PowerPoint, Media, Archives, ISO)"; Types: full compact custom; Flags: fixed
Name: "ocr"; Description: "Local Tesseract OCR Engine (Offline Image and PDF Text Recognition)"; Types: full
Name: "whisper"; Description: "Local Whisper AI Model (Offline Audio and Video Speech-to-Text)"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\OmniConvert\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\bin\tesseract\*"; DestDir: "{app}\bin\tesseract"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: ocr
Source: "..\resources\models\whisper\*"; DestDir: "{app}\resources\models\whisper"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: whisper

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
