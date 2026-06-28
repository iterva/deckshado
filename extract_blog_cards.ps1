Add-Type -AssemblyName System.Drawing

$srcDir = 'Proyecto-deckshado/cartas-blog3'
$outDir = Join-Path $srcDir 'extracted'
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

function Save-Crop {
    param(
        [Parameter(Mandatory=$true)] [System.Drawing.Image]$Image,
        [Parameter(Mandatory=$true)] [int]$X,
        [Parameter(Mandatory=$true)] [int]$Y,
        [Parameter(Mandatory=$true)] [int]$Width,
        [Parameter(Mandatory=$true)] [int]$Height,
        [Parameter(Mandatory=$true)] [string]$OutputPath
    )

    $bmp = [System.Drawing.Bitmap]::new($Width, $Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $srcRect = [System.Drawing.Rectangle]::new($X, $Y, $Width, $Height)
    $dstRect = [System.Drawing.Rectangle]::new(0, 0, $Width, $Height)
    $g.DrawImage($Image, $dstRect, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    $bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

# Singles
$singleMap = @{
    'Satanas_0.png' = 'Satanas'
    'Demonios_del_abismo_17.png' = 'Demonios_del_Abismo'
    'Lahmu_Inmortal_0.png' = 'Lahmu_Inmortal'
    'Nefandos_194.png' = 'Nefandos'
    'Escamas_de_Azi_229.png' = 'Escamas_de_Azi'
    'Gran_Dragon_3.png' = 'Gran_Dragon'
    'Leviathan_4.png' = 'Leviathan'
    'Wyrm_de_la_Plaga_8.png' = 'Wyrm_de_la_Plaga'
    'Lucifer_9.png' = 'Lucifer'
    'Morgana_09.png' = 'Morgana'
}

# Doubles (left, right)
$doubleMap = @{
    'd5_46c77f68-7677-4320-94f1-0b0c696f2940.png' = @('Baphomet', 'Furfur')
    'd1_6ed5cab9-f3c8-450b-8008-8318f873bc24.png' = @('Belcebu', 'Asmodeus')
    'd2_7e83f45a-56dd-4d82-985d-de86053e6433.png' = @('Samael', 'Azrael')
    'd3_5d5e5345-b3c4-458f-a668-2a207be87e92.png' = @('Titan_Abismal', 'Titan_Nephilim')
    'd4_0ef04ab6-91f8-47f9-8a79-bb4cdefd6ce9.png' = @('Cuerno_de_Titan', 'Rugido_de_Titan')
    'azi_2.png' = @('Azi_Raoioita', 'Valefor')
}

# Triple (left, center, right)
$tripleFile = 'azi_1.png'
$tripleNames = @('Azi_Demoniaco', 'Azi_del_Abismo', 'Dagon')

$manifest = @()

foreach ($entry in $singleMap.GetEnumerator()) {
    $src = Join-Path $srcDir $entry.Key
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $outDir ($entry.Value + '.png')
    Copy-Item $src $dst -Force
    $img = [System.Drawing.Image]::FromFile((Resolve-Path $dst))
    $manifest += [PSCustomObject]@{
        card = $entry.Value
        source = $entry.Key
        mode = 'single-copy'
        file = $dst
        width = $img.Width
        height = $img.Height
    }
    $img.Dispose()
}

foreach ($entry in $doubleMap.GetEnumerator()) {
    $src = Join-Path $srcDir $entry.Key
    if (-not (Test-Path $src)) { continue }

    $img = [System.Drawing.Image]::FromFile((Resolve-Path $src))
    [int]$w = $img.Width
    [int]$h = $img.Height
    [int]$half = [Math]::Floor($w / 2)

    $leftName = $entry.Value[0]
    $rightName = $entry.Value[1]

    $leftOut = Join-Path $outDir ($leftName + '.png')
    $rightOut = Join-Path $outDir ($rightName + '.png')

    Save-Crop -Image $img -X 0 -Y 0 -Width $half -Height $h -OutputPath $leftOut
    Save-Crop -Image $img -X $half -Y 0 -Width ($w - $half) -Height $h -OutputPath $rightOut

    $manifest += [PSCustomObject]@{ card=$leftName; source=$entry.Key; mode='split-left'; file=$leftOut; width=$half; height=$h }
    $manifest += [PSCustomObject]@{ card=$rightName; source=$entry.Key; mode='split-right'; file=$rightOut; width=($w-$half); height=$h }

    $img.Dispose()
}

$triplePath = Join-Path $srcDir $tripleFile
if (Test-Path $triplePath) {
    $img = [System.Drawing.Image]::FromFile((Resolve-Path $triplePath))
    [int]$w = $img.Width
    [int]$h = $img.Height

    [int]$s1 = [Math]::Floor($w / 3)
    [int]$s2 = [Math]::Floor($w / 3)
    [int]$s3 = $w - $s1 - $s2

    $o1 = Join-Path $outDir ($tripleNames[0] + '.png')
    $o2 = Join-Path $outDir ($tripleNames[1] + '.png')
    $o3 = Join-Path $outDir ($tripleNames[2] + '.png')

    Save-Crop -Image $img -X 0 -Y 0 -Width $s1 -Height $h -OutputPath $o1
    Save-Crop -Image $img -X $s1 -Y 0 -Width $s2 -Height $h -OutputPath $o2
    Save-Crop -Image $img -X ($s1 + $s2) -Y 0 -Width $s3 -Height $h -OutputPath $o3

    $manifest += [PSCustomObject]@{ card=$tripleNames[0]; source=$tripleFile; mode='split-1'; file=$o1; width=$s1; height=$h }
    $manifest += [PSCustomObject]@{ card=$tripleNames[1]; source=$tripleFile; mode='split-2'; file=$o2; width=$s2; height=$h }
    $manifest += [PSCustomObject]@{ card=$tripleNames[2]; source=$tripleFile; mode='split-3'; file=$o3; width=$s3; height=$h }

    $img.Dispose()
}

$manifest = $manifest | Sort-Object card
$manifestPath = Join-Path $outDir 'manifest.csv'
$manifest | Export-Csv -Path $manifestPath -NoTypeInformation -Encoding UTF8

Write-Host "Cards extracted:" $manifest.Count
Write-Host "Manifest:" $manifestPath
