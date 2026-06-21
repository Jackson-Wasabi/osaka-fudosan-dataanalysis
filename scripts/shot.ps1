# 画面キャプチャ専用スクリプト（短いコマンドで安定呼び出し用）
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
try {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $path = Join-Path $env:TEMP 'tab_shot.png'
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output ("OK " + $path + " " + $b.Width + "x" + $b.Height)
} catch {
    Write-Output ("ERR " + $_.Exception.Message)
}
