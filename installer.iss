; Inno Setup 6 - tao bo cai dat Echem Studio.  Chay build.bat truoc, roi build_setup.bat.
; Cai vao thu muc cua NGUOI DUNG (khong can quyen Admin) de tu cap nhat duoc ma_nguon.
#define TenApp "Echem Studio"
#define Exe "DienHoaOrigin.exe"

[Setup]
AppId={{7C3A1E52-5B7E-4E0B-9A55-0E57D1C0A111}
AppName={#TenApp}
AppVersion=1.0
DefaultDirName={localappdata}\EchemStudio
DefaultGroupName={#TenApp}
PrivilegesRequired=lowest
OutputDir=setup
OutputBaseFilename=EchemStudio_Setup
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tao bieu tuong tren Desktop"; Flags: unchecked

[Files]
Source: "dist\DienHoaOrigin\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#TenApp}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#TenApp}"; Filename: "{app}\{#Exe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#Exe}"; Description: "Mo {#TenApp}"; Flags: nowait postinstall skipifsilent
