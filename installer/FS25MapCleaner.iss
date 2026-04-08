\
    #define MyAppName "FS25 Map Cleaner"
    #define MyAppVersion "1.1.0"
    #define MyAppPublisher "FS25 Map Cleaner"
    #define MyAppExeName "FS25MapCleaner.exe"

    [Setup]
    AppId={{6E97B2AB-598B-4A4A-A44E-919C7B9EDB96}
    AppName={#MyAppName}
    AppVersion={#MyAppVersion}
    AppPublisher={#MyAppPublisher}
    DefaultDirName={localappdata}\Programs\FS25 Map Cleaner
    DisableDirPage=no
    DefaultGroupName=FS25 Map Cleaner
    AllowNoIcons=yes
    Compression=lzma
    SolidCompression=yes
    WizardStyle=modern
    SetupIconFile=assets\fs25_map_cleaner.ico
    UninstallDisplayIcon={app}\{#MyAppExeName}
    OutputDir=installer\output
    OutputBaseFilename=FS25MapCleaner_Setup
    ArchitecturesInstallIn64BitMode=x64compatible
    ChangesAssociations=no
    PrivilegesRequired=lowest
    PrivilegesRequiredOverridesAllowed=dialog
    DisableProgramGroupPage=yes

    [Languages]
    Name: "english"; MessagesFile: "compiler:Default.isl"

    [Tasks]
    Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

    [Files]
    Source: "dist\FS25MapCleaner.exe"; DestDir: "{app}"; Flags: ignoreversion
    Source: "assets\fs25_map_cleaner.ico"; DestDir: "{app}"; Flags: ignoreversion

    [Icons]
    Name: "{autoprograms}\FS25 Map Cleaner"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\fs25_map_cleaner.ico"
    Name: "{autodesktop}\FS25 Map Cleaner"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\fs25_map_cleaner.ico"

    [Run]
    Filename: "{app}\{#MyAppExeName}"; Description: "Launch FS25 Map Cleaner"; Flags: nowait postinstall skipifsilent
