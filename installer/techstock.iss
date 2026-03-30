; ============================================================
; TechStock v4.0 — Inno Setup Installer Script
; Instalar / Actualizar / Reparar / Desinstalar
; Incluye PostgreSQL portable + servidor web completo
; NO requiere software adicional en la maquina destino
; DATOS en %APPDATA%\TechStock NUNCA se tocan en update/repair
; ============================================================

#define MyAppName "TechStock"
#define MyAppVersion "4.0"
#define MyAppPublisher "Orionics"
#define MyAppURL "https://orionics.com"
#define MyAppExeName "TechStock.exe"
#define MyAppDescription "Sistema de Inventario y Punto de Venta"

[Setup]
AppId={{8F4B3C2E-1A5D-4E7F-9B0C-6D8E2F1A3B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=TechStock_Setup_v{#MyAppVersion}
; Compresion optimizada para instalacion rapida
Compression=lzma2/fast
SolidCompression=yes
LZMANumBlockThreads=4
LZMAUseSeparateProcess=yes
; SetupIconFile=..\static\favicon.ico
WizardStyle=modern
WizardSizePercent=110
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} v{#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
; ── Actualizacion: reutilizar carpeta anterior ──
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
CloseApplications=yes
RestartApplications=no
; Espacio extra para datos de PostgreSQL
ExtraDiskSpaceRequired=52428800
; Optimizaciones de velocidad
DisableDirPage=auto
DisableProgramGroupPage=auto
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Instalacion completa (recomendado)"
Name: "custom"; Description: "Instalacion personalizada"; Flags: iscustom

[Components]
Name: "main"; Description: "Aplicacion TechStock"; Types: full custom; Flags: fixed
Name: "pgsql"; Description: "PostgreSQL 16 (motor de base de datos)"; Types: full custom; Flags: fixed
Name: "shortcuts"; Description: "Accesos directos (Escritorio y Menu Inicio)"; Types: full

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el &Escritorio"; GroupDescription: "Accesos directos:"; Components: shortcuts
Name: "startmenu"; Description: "Crear acceso en el &Menu Inicio"; GroupDescription: "Accesos directos:"; Components: shortcuts; Flags: checkedonce
Name: "autostart"; Description: "Iniciar TechStock con &Windows"; GroupDescription: "Opciones adicionales:"; Flags: unchecked

[Files]
; Application files (PyInstaller dist) — todo excepto pgsql
Source: "..\dist\TechStock\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main; Excludes: "pgsql"
; PostgreSQL portable (ya optimizado, sin docs/pgAdmin/headers)
Source: "..\dist\TechStock\pgsql\*"; DestDir: "{app}\pgsql"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: pgsql
; Preservar clave secreta existente — nunca sobreescribir
; (no se incluye .secret_key en los archivos fuente, se genera al ejecutar)

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  Comment: "{#MyAppDescription}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  Comment: "{#MyAppDescription}"; Tasks: startmenu
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  Comment: "Iniciar {#MyAppName} automaticamente"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop PostgreSQL and TechStock before uninstall
Filename: "{app}\pgsql\bin\pg_ctl.exe"; Parameters: "stop -D ""{userappdata}\TechStock\pgdata"" -m fast"; \
  Flags: runhidden skipifdoesntexist; RunOnceId: "StopPG"
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\.secret_key"

[Messages]
spanish.BeveledLabel=TechStock - Sistema de Inventario
spanish.WelcomeLabel1=Bienvenido al asistente de {#MyAppName}
spanish.WelcomeLabel2=Este asistente le permitira instalar, actualizar, reparar o desinstalar {#MyAppName} v{#MyAppVersion}.%n%nIncluye todo lo necesario:%n  - Servidor web (FastAPI + Uvicorn)%n  - Base de datos PostgreSQL 16%n  - Interfaz completa del sistema%n%nNo requiere software adicional.%nFunciona en cualquier PC con Windows 10 o superior.
spanish.FinishedHeadingLabel=Operacion completada
spanish.FinishedLabel={#MyAppName} se ha instalado correctamente.%n%nLa base de datos se inicializara automaticamente la primera vez que inicie la aplicacion.%n%nSus datos existentes no fueron modificados.

[Code]

var
  MaintenancePage: TInputOptionWizardPage;
  IsMaintenanceMode: Boolean;
  InstalledVersion: String;
  IsUpgrade: Boolean;

procedure CreateDataDir();
begin
  ForceDirectories(ExpandConstant('{userappdata}\TechStock'));
  ForceDirectories(ExpandConstant('{userappdata}\TechStock\pgdata'));
  ForceDirectories(ExpandConstant('{userappdata}\TechStock\backups'));
end;

function IsAlreadyInstalled(): Boolean;
begin
  Result := RegValueExists(HKEY_CURRENT_USER,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F4B3C2E-1A5D-4E7F-9B0C-6D8E2F1A3B5C}_is1',
    'UninstallString');
end;

function GetInstalledVersion(): String;
var
  S: String;
begin
  Result := '';
  if RegQueryStringValue(HKEY_CURRENT_USER,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F4B3C2E-1A5D-4E7F-9B0C-6D8E2F1A3B5C}_is1',
    'DisplayVersion', S) then
  begin
    Result := S;
  end;
end;

function GetUninstallString(): String;
var
  S: String;
begin
  Result := '';
  if RegQueryStringValue(HKEY_CURRENT_USER,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F4B3C2E-1A5D-4E7F-9B0C-6D8E2F1A3B5C}_is1',
    'UninstallString', S) then
  begin
    Result := RemoveQuotes(S);
  end;
end;

procedure InitializeWizard();
var
  OptionLabel: String;
begin
  IsMaintenanceMode := IsAlreadyInstalled();
  InstalledVersion := GetInstalledVersion();
  IsUpgrade := IsMaintenanceMode and (InstalledVersion <> '{#MyAppVersion}');

  if IsMaintenanceMode then
  begin
    if IsUpgrade then
    begin
      // Show update + repair + uninstall options
      MaintenancePage := CreateInputOptionPage(wpWelcome,
        'TechStock v' + InstalledVersion + ' esta instalado',
        'Se detecta una nueva version disponible (v{#MyAppVersion}):',
        'Elija una opcion y presione Siguiente para continuar.',
        True, False);
      MaintenancePage.Add('Actualizar a v{#MyAppVersion} — Instala la nueva version conservando todos sus datos');
      MaintenancePage.Add('Reparar — Reinstala los archivos del programa sin afectar sus datos');
      MaintenancePage.Add('Desinstalar — Elimina TechStock completamente de este equipo');
      MaintenancePage.Values[0] := True;  // Default: Update
    end
    else
    begin
      // Same version — repair or uninstall
      MaintenancePage := CreateInputOptionPage(wpWelcome,
        'TechStock v{#MyAppVersion} ya esta instalado',
        'Seleccione la operacion que desea realizar:',
        'Elija una opcion y presione Siguiente para continuar.',
        True, False);
      MaintenancePage.Add('Reparar — Reinstala todos los archivos del programa sin afectar sus datos');
      MaintenancePage.Add('Desinstalar — Elimina TechStock completamente de este equipo');
      MaintenancePage.Values[0] := True;  // Default: Repair
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;

  if IsMaintenanceMode then
  begin
    // In maintenance mode (repair/update), skip component/task/dir selection
    if IsUpgrade then
    begin
      // Update or Repair selected (options 0 or 1)
      if MaintenancePage.Values[0] or MaintenancePage.Values[1] then
      begin
        if (PageID = wpSelectComponents) or (PageID = wpSelectTasks) or
           (PageID = wpSelectDir) or (PageID = wpSelectProgramGroup) then
          Result := True;
      end;
    end
    else
    begin
      // Same version — Repair selected (option 0)
      if MaintenancePage.Values[0] then
      begin
        if (PageID = wpSelectComponents) or (PageID = wpSelectTasks) or
           (PageID = wpSelectDir) or (PageID = wpSelectProgramGroup) then
          Result := True;
      end;
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  UninstallExe: String;
  ResultCode: Integer;
  UninstallIdx: Integer;
begin
  Result := True;

  if IsMaintenanceMode and (CurPageID = MaintenancePage.ID) then
  begin
    // Determine uninstall option index based on mode
    if IsUpgrade then
      UninstallIdx := 2   // 3rd option in upgrade mode
    else
      UninstallIdx := 1;  // 2nd option in same-version mode

    if MaintenancePage.Values[UninstallIdx] then
    begin
      // User chose UNINSTALL
      UninstallExe := GetUninstallString();
      if UninstallExe <> '' then
      begin
        if MsgBox(
          'Se procedera a desinstalar TechStock.' + #13#10 + #13#10 +
          'Importante: Sus datos de la base de datos se pueden conservar.' + #13#10 +
          'Se le preguntara durante la desinstalacion.' + #13#10 + #13#10 +
          'Desea continuar?',
          mbConfirmation, MB_YESNO) = IDYES then
        begin
          Exec(UninstallExe, '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
        end;
      end;
      Result := False;
      WizardForm.Close();
    end;
    // If Update or Repair selected, continue normally (install files)
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure BackupSecretKey();
var
  Src, Dst: String;
begin
  Src := ExpandConstant('{app}\.secret_key');
  Dst := ExpandConstant('{userappdata}\TechStock\.secret_key.bak');
  if FileExists(Src) then
    FileCopy(Src, Dst, False);
end;

procedure RestoreSecretKey();
var
  Src, Dst: String;
begin
  Src := ExpandConstant('{userappdata}\TechStock\.secret_key.bak');
  Dst := ExpandConstant('{app}\.secret_key');
  if FileExists(Src) then
  begin
    FileCopy(Src, Dst, False);
    DeleteFile(Src);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  KillResult: Integer;
begin
  if CurStep = ssInstall then
  begin
    // Backup the secret key so sessions survive the update
    BackupSecretKey();

    // Stop PostgreSQL if running
    Exec(ExpandConstant('{app}\pgsql\bin\pg_ctl.exe'),
         'stop -D "' + ExpandConstant('{userappdata}\TechStock\pgdata') + '" -m fast',
         '', SW_HIDE, ewWaitUntilTerminated, KillResult);
    // Kill TechStock
    Exec('taskkill', '/F /IM TechStock.exe', '', SW_HIDE, ewWaitUntilTerminated, KillResult);
    // Brief pause to ensure file handles are released
    Sleep(1000);
  end;

  if CurStep = ssPostInstall then
  begin
    // Restore secret key after file replacement
    RestoreSecretKey();
    // Ensure data directories exist
    CreateDataDir();
  end;
end;

function InitializeUninstall(): Boolean;
var
  KeepData: Integer;
  KillResult: Integer;
begin
  Result := True;

  // Stop services before uninstalling
  Exec(ExpandConstant('{app}\pgsql\bin\pg_ctl.exe'),
       'stop -D "' + ExpandConstant('{userappdata}\TechStock\pgdata') + '" -m fast',
       '', SW_HIDE, ewWaitUntilTerminated, KillResult);
  Exec('taskkill', '/F /IM TechStock.exe', '', SW_HIDE, ewWaitUntilTerminated, KillResult);

  KeepData := MsgBox(
    'Desea conservar la base de datos y sus datos?' + #13#10 +
    '(Se encuentran en ' + ExpandConstant('{userappdata}\TechStock') + ')' + #13#10 + #13#10 +
    'SI — Conservar datos (recomendado si va a reinstalar o actualizar)' + #13#10 +
    'NO — Eliminar todo permanentemente (IRREVERSIBLE)',
    mbConfirmation, MB_YESNO);
  if KeepData = IDNO then
  begin
    if MsgBox(
      'ATENCION: Se eliminaran TODOS los datos del negocio:' + #13#10 +
      '- Productos, ventas, inventario' + #13#10 +
      '- Clientes, proveedores, facturas' + #13#10 +
      '- Configuracion y usuarios' + #13#10 + #13#10 +
      'Esta seguro? Esta accion NO se puede deshacer.',
      mbError, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\TechStock'), True, True, True);
    end;
  end;
end;
