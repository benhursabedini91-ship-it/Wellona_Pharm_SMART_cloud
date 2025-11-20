; AutoHotkey v1 script – imports XMLs from queue and proknjizuje
#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
SetTitleMatchMode, 2

QueuePath := A_Args.Length() >= 1 ? A_Args[1] : "C:\\Wellona\\wphAI\\queue\\erp_import\\" . A_YYYY . A_MM . A_DD
WinTitle  := A_Args.Length() >= 2 ? A_Args[2] : "EASYBUSINESS"
DlgTitle  := A_Args.Length() >= 3 ? A_Args[3] : "Open"
NavMode   := A_Args.Length() >= 4 ? A_Args[4] : "context"  ; context menu navigation
CtxIdx    := A_Args.Length() >= 5 ? A_Args[5] : "2"        ; 2 = MP Kalkulacija
PreuzKey  := A_Args.Length() >= 6 ? A_Args[6] : ""         ; optional
ProkAlt   := A_Args.Length() >= 7 ? A_Args[7] : "!p"
ExePath   := A_Args.Length() >= 8 ? A_Args[8] : ""
PreX      := A_Args.Length() >= 9 ? A_Args[9] : "560"
PreY      := A_Args.Length() >= 10 ? A_Args[10] : "86"
ProX      := A_Args.Length() >= 11 ? A_Args[11] : "618"
ProY      := A_Args.Length() >= 12 ? A_Args[12] : "148"
VendorIdx := A_Args.Length() >= 13 ? A_Args[13] : "5"
VendorKey := A_Args.Length() >= 14 ? A_Args[14] : "s"

if (!FileExist(QueuePath)) {
  MsgBox, 16, commit_erp, Queue path not found: %QueuePath%
  ExitApp 2
}

; Start ERP if not running
IfWinNotExist, %WinTitle%
{
  if (ExePath != "")
  {
    Run, %ExePath%
    Sleep, 1500
  }
}

; Optional login if dialog visible
IfWinExist, PREPOZNAVANJE KORISNIKA
{
  WinActivate
  Sleep, 200
  ; default sequence 1{TAB}1{ENTER}
  Send, 1{TAB}1{ENTER}
  Sleep, 500
}

Loop, Files, %QueuePath%\*.xml
{
  xml := A_LoopFileFullPath
  ; Activate ERP
  WinActivate, %WinTitle%
  WinWaitActive, %WinTitle%, , 10
  Sleep, 300

  ; Navigate to MP Kalkulacija via context menu
  if (NavMode = "context")
  {
    CoordMode, Mouse, Window
    WinGetPos, X, Y, W, H, %WinTitle%
    cx := X + (W/2)
    cy := Y + (H/2)
    MouseMove, %cx%, %cy%, 0
    Click, Right
    Sleep, 250
    ; Ensure focus at first item, then move down (MenuIndex-1)
    Send, {Home}
    Sleep, 120
    idx := CtxIdx - 1
    Loop, %idx%
    {
      Send, {Down}
      Sleep, 80
    }
    Send, {Enter}
    Sleep, 600
  }

  ; In MP form: New (Alt+N) per screenshot
  Send, !n
  Sleep, 200

  ; Click 'Preuzmi' (no shortcut): simulate real mouse click in WINDOW coords
  CoordMode, Mouse, Window
  WinGetPos, mX, mY, mW, mH, KALKULACIJA MALOPRODAJE
  if (mW != "")
  {
    px := mX + PreX
    py := mY + PreY
    MouseClick, Left, %px%, %py%, 1, 0
    Sleep, 220
  }
  else if (PreuzKey != "")
  {
    Send, %PreuzKey%
  }
  else
  {
    ; fallback center click
    MouseClick, Left, %cx%, %cy%
    Sleep, 200
  }

  ; Try to select supplier and open file dialog (prefer index navigation: Down x VendorIdx)
  success := false
  attempt := 0
  Loop, 4
  {
    attempt++
    ; ensure menu is open (click again each attempt; try arrow area too)
    MouseClick, Left, %px%, %py%, 1, 0
    Sleep, 160
    if (attempt > 1) {
      px2 := px + 14  ; nudge to the right to hit the dropdown arrow
      MouseClick, Left, %px2%, %py%, 1, 0
      Sleep, 160
    }
    ; index navigation first
    idx2 := VendorIdx - 1
    Send, {Home}
    Sleep, 80
    Loop, %idx2%
    {
      Send, {Down}
      Sleep, 60
    }
    Send, {Enter}
    Sleep, 400
    WinWait, ahk_class #32770,, 1
    if (!ErrorLevel)
    {
      success := true
      break
    }
    ; fallback: first-letter hotkey (e.g., 's')
    Send, %VendorKey%{Enter}
    Sleep, 400
    WinWait, ahk_class #32770,, 1
    if (!ErrorLevel)
    {
      success := true
      break
    }
    ; last resort: nudge click a bit more and retry next loop
    px := px + 10
  }
  if (!success) {
    MsgBox, 16, commit_erp, Open dialog not detected. Aborting this XML.
    continue
  }
  ; at this point common File Open dialog should be active (class #32770)
  WinActivate, ahk_class #32770
  Sleep, 150
  ; Ensure the File name field gets the full path and click Open (focus Edit1 explicitly)
  ControlFocus, Edit1, ahk_class #32770
  Sleep, 60
  ControlSetText, Edit1, %xml%, ahk_class #32770
  Sleep, 120
  ControlClick, Button1, ahk_class #32770
  ; If dialog is still open, navigate via address bar and pick target file
  WinWaitClose, ahk_class #32770, , 1
  if (ErrorLevel)
  {
    SplitPath, xml, _file, _dir
    ; Focus address bar, navigate to directory
    Send, !d
    Sleep, 120
    Send, %_dir%{Enter}
    Sleep, 300
    ; Type filename and open
    Send, %_file%{Enter}
    WinWaitClose, ahk_class #32770, , 1
  }
  ; wait a little for import to finish
  Sleep, 1200

  ; Proknjizi
  if (ProkAlt != "")
  {
    Send, %ProkAlt%
  }
  else
  {
    ; try clicking approximate proknjizi button (client coords)
    if (mW != "")
    {
      px2 := ProX
      py2 := ProY
      ControlClick, x%px2% y%py2%, KALKULACIJA MALOPRODAJE,, Left, 1, NA
    }
  }
  Sleep, 600
}

ExitApp 0
