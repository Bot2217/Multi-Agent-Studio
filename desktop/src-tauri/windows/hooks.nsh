; Stop only this install's ulei.exe and ulei-backend.exe before NSIS copies files.
; A foreign process that still holds the sidecar must abort the install.
!define ULEI_HOOK_DIR "${__FILEDIR__}"

!macro Ulei.ReleaseInstallLock
  InitPluginsDir
  File /oname=$PLUGINSDIR\install-lock.ps1 "${ULEI_HOOK_DIR}\install-lock.ps1"
  nsExec::ExecToLog '"$WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install-lock.ps1" -InstallDir "$INSTDIR"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Не удалось обновить «Улей».$\r$\n$\r$\nФайл ulei-backend.exe в папке установки занят, и установщик не стал заменять программу наполовину.$\r$\nЗакройте «Улей» полностью, включая фоновый ulei-backend.exe, и запустите установщик ещё раз.$\r$\n$\r$\nНастройки в %APPDATA%\ulei и локальные модели не удалялись."
    Abort
  ${EndIf}
  SetOverwrite on
  ClearErrors
  Delete "$INSTDIR\ulei-backend.exe"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "Не удалось заменить ulei-backend.exe. Закройте «Улей» и повторите установку. Настройки и модели не удалялись."
    Abort
  ${EndIf}
  ClearErrors
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro Ulei.ReleaseInstallLock
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro Ulei.ReleaseInstallLock
!macroend
