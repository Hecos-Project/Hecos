Add-Type -AssemblyName PresentationCore
$p = New-Object System.Windows.Media.MediaPlayer
$p.Open($env:HECOS_SOUND_PATH)
$p.Play()
Start-Sleep -Milliseconds 200
while ($p.Position -lt $p.NaturalDuration.TimeSpan) { Start-Sleep -Milliseconds 100 }
