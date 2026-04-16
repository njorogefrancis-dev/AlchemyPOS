; AlchemyPOS — NSIS Installer Script
; Requires: NSIS (https://nsis.sourceforge.io/)
; Usage: makensis installer.nsi

!include "MUI2.nsh"
!include "x64.nsh"

; ─────────────────────────────────────────────────────────────────────────────
; Configuration
; ─────────────────────────────────────────────────────────────────────────────
Name "AlchemyPOS"
OutFile "..\dist\AlchemyPOS_Installer.exe"
InstallDir "$PROGRAMFILES\AlchemyPOS"
InstallDirRegKey HKCU "Software\AlchemyPOS" "InstallDir"

; Request admin privileges for installation
RequestExecutionLevel admin

; ─────────────────────────────────────────────────────────────────────────────
; MUI Settings
; ─────────────────────────────────────────────────────────────────────────────
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "AlchemyPOS Installation"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of AlchemyPOS - Professional Point of Sale System.$\n$\nClick Next to continue."

; ─────────────────────────────────────────────────────────────────────────────
; Pages
; ─────────────────────────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ═════════════════════════════════════════════════════════════════════════════
; Installer Sections
; ═════════════════════════════════════════════════════════════════════════════

Section "AlchemyPOS (Required)" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  
  ; Copy main executable
  File "..\dist\AlchemyPOS.exe"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Create registry entries
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "DisplayName" "AlchemyPOS"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "Publisher" "AlchemyPOS"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "DisplayVersion" "1.0.0"
  WriteRegDWord HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "NoModify" 1
  WriteRegDWord HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS" "NoRepair" 1
SectionEnd

Section "Desktop Shortcut" SecShortcut
  SetShellVarContext current
  CreateShortCut "$DESKTOP\AlchemyPOS.lnk" "$INSTDIR\AlchemyPOS.exe" "" "$INSTDIR\AlchemyPOS.exe" 0
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
  SetShellVarContext current
  CreateDirectory "$SMPROGRAMS\AlchemyPOS"
  CreateShortCut "$SMPROGRAMS\AlchemyPOS\AlchemyPOS.lnk" "$INSTDIR\AlchemyPOS.exe"
  CreateShortCut "$SMPROGRAMS\AlchemyPOS\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

; Set section descriptions
LangString DESC_SecMain ${LANG_ENGLISH} "AlchemyPOS application and required files"
LangString DESC_SecShortcut ${LANG_ENGLISH} "Create a shortcut on the desktop"
LangString DESC_SecStartMenu ${LANG_ENGLISH} "Create shortcuts in the Start Menu"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcut} $(DESC_SecShortcut)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ═════════════════════════════════════════════════════════════════════════════
; Uninstaller Section
; ═════════════════════════════════════════════════════════════════════════════

Section "Uninstall"
  SetShellVarContext current
  
  ; Remove files
  Delete "$INSTDIR\AlchemyPOS.exe"
  Delete "$INSTDIR\uninstall.exe"
  
  ; Remove directories
  RMDir "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$DESKTOP\AlchemyPOS.lnk"
  Delete "$SMPROGRAMS\AlchemyPOS\AlchemyPOS.lnk"
  Delete "$SMPROGRAMS\AlchemyPOS\Uninstall.lnk"
  RMDir "$SMPROGRAMS\AlchemyPOS"
  
  ; Remove registry entries
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AlchemyPOS"
  DeleteRegKey HKCU "Software\AlchemyPOS"
SectionEnd

; ─────────────────────────────────────────────────────────────────────────────
; Functions
; ─────────────────────────────────────────────────────────────────────────────

Function .onInit
  ${If} ${RunningX64}
    ; 64-bit system
  ${EndIf}
FunctionEnd

Function un.onInit
  SetShellVarContext current
FunctionEnd
