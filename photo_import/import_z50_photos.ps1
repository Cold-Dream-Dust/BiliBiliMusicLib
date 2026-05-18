[CmdletBinding()]
param(
    [string]$DeviceNamePattern = "Z 50",
    [string]$SourceSubPath = "可移动存储\DCIM\100NZ_50",
    [string]$DestinationRoot = "F:\\Z50_Photos_Import",
    [int]$MaxFilesPerBatch = 120,
    [object]$MaxBatchBytes = 2GB,
    [int]$MaxRetryPerFile = 2,
    [int]$CopyTimeoutSeconds = 120,
    [switch]$KeepSourceOnDevice,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$time] $Message"
}

function Resolve-ByteSize {
    param([object]$Value)

    if ($Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or $Value -is [int64]) {
        return [int64]$Value
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "MaxBatchBytes cannot be empty."
    }

    $trimmed = $text.Trim()
    if ($trimmed -notmatch '^(?<number>\d+(?:\.\d+)?)\s*(?<unit>B|KB|MB|GB|TB)?$') {
        throw "Unsupported MaxBatchBytes value: '$trimmed'. Use values like 1073741824, 500MB, or 1GB."
    }

    $number = [double]$matches['number']
    $unit = $matches['unit'].ToUpperInvariant()
    $multiplier = switch ($unit) {
        '' { 1 }
        'B' { 1 }
        'KB' { 1KB }
        'MB' { 1MB }
        'GB' { 1GB }
        'TB' { 1TB }
        default {
            throw "Unsupported MaxBatchBytes unit: '$unit'."
        }
    }

    return [int64][math]::Round($number * $multiplier)
}

function Get-StatePath {
    param([string]$BaseDir)
    Join-Path $BaseDir ".import_state_z50.json"
}

function New-InitialState {
    param(
        [string]$DevicePattern,
        [string]$SourcePath,
        [string]$DestRoot
    )

    [ordered]@{
        version = 1
        createdAt = (Get-Date).ToString("o")
        lastRunAt = $null
        devicePattern = $DevicePattern
        sourceSubPath = $SourcePath
        destinationRoot = $DestRoot
        completedBatches = @()
        importedFiles = @{}
    }
}

function Load-State {
    param(
        [string]$BaseDir,
        [string]$DevicePattern,
        [string]$SourcePath,
        [string]$DestRoot
    )

    $statePath = Get-StatePath -BaseDir $BaseDir
    if (-not (Test-Path -LiteralPath $statePath)) {
        return (New-InitialState -DevicePattern $DevicePattern -SourcePath $SourcePath -DestRoot $DestRoot)
    }

    try {
        $raw = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return (New-InitialState -DevicePattern $DevicePattern -SourcePath $SourcePath -DestRoot $DestRoot)
        }

        $loaded = $raw | ConvertFrom-Json
        if (-not ($loaded.PSObject.Properties.Name -contains 'importedFiles')) {
            $loaded | Add-Member -MemberType NoteProperty -Name importedFiles -Value @{}
        }
        elseif ($null -eq $loaded.importedFiles) {
            $loaded.importedFiles = @{}
        }
        if (-not ($loaded.PSObject.Properties.Name -contains 'completedBatches')) {
            $loaded | Add-Member -MemberType NoteProperty -Name completedBatches -Value @()
        }
        elseif ($null -eq $loaded.completedBatches) {
            $loaded.completedBatches = @()
        }
        return $loaded
    }
    catch {
        throw "Failed to load state file: $statePath. $($_.Exception.Message)"
    }
}

function Save-State {
    param(
        [string]$BaseDir,
        [object]$State
    )

    $State.lastRunAt = (Get-Date).ToString("o")
    $statePath = Get-StatePath -BaseDir $BaseDir
    $json = $State | ConvertTo-Json -Depth 64
    Set-Content -LiteralPath $statePath -Value $json -Encoding UTF8
}

function Get-ThisPcFolder {
    $shell = New-Object -ComObject Shell.Application
    $thisPc = $shell.Namespace(17)
    if (-not $thisPc) {
        throw "Cannot access This PC shell namespace."
    }

    return @{
        Shell = $shell
        ThisPc = $thisPc
    }
}

function Open-ShellFolder {
    param(
        [object]$Shell,
        [object]$Item
    )

    if (-not $Item) {
        return $null
    }

    try {
        $folder = $Item.GetFolder
        if ($folder) {
            return $folder
        }
    }
    catch {
    }

    try {
        return $Shell.Namespace($Item.Path)
    }
    catch {
        return $null
    }
}

function Find-DeviceFolder {
    param(
        [object]$Shell,
        [object]$ThisPc,
        [string]$Pattern
    )

    $deviceItem = $null
    foreach ($item in @($ThisPc.Items())) {
        if ($item.Name -like "*$Pattern*") {
            $deviceItem = $item
            break
        }
    }

    if (-not $deviceItem) {
        throw "Device with name pattern '$Pattern' was not found under This PC."
    }

    $deviceFolder = Open-ShellFolder -Shell $Shell -Item $deviceItem
    if (-not $deviceFolder) {
        throw "Device folder cannot be opened: $($deviceItem.Name)"
    }

    return @{
        Item = $deviceItem
        Folder = $deviceFolder
    }
}

function Get-ChildFolderByName {
    param(
        [object]$Shell,
        [object]$ParentFolder,
        [string]$Name
    )

    foreach ($item in @($ParentFolder.Items())) {
        if ($item.IsFolder -and $item.Name -eq $Name) {
            $sub = Open-ShellFolder -Shell $Shell -Item $item
            if ($sub) {
                return $sub
            }
        }
    }

    return $null
}

function Resolve-SourceFolder {
    param(
        [object]$Shell,
        [object]$DeviceFolder,
        [string]$SubPath
    )

    $parts = $SubPath.Split([char]'\', [System.StringSplitOptions]::RemoveEmptyEntries)
    $current = $DeviceFolder

    foreach ($part in $parts) {
        $next = Get-ChildFolderByName -Shell $Shell -ParentFolder $current -Name $part
        if (-not $next) {
            throw "Source path part '$part' not found on device for sub path '$SubPath'."
        }
        $current = $next
    }

    return $current
}

function Get-FileKey {
    param(
        [string]$RelativePath,
        [int64]$Size,
        [datetime]$Modified
    )

    $mod = $Modified.ToString("yyyy-MM-ddTHH:mm:ss")
    return "$RelativePath|$Size|$mod"
}

function Get-ShellItemSizeBytes {
    param([object]$Item)

    try {
        $extendedSize = $Item.ExtendedProperty('System.Size')
        if ($null -ne $extendedSize -and [int64]$extendedSize -gt 0) {
            return [int64]$extendedSize
        }
    }
    catch {
    }

    try {
        $directSize = $Item.Size
        if ($null -ne $directSize -and [int64]$directSize -gt 0) {
            return [int64]$directSize
        }
    }
    catch {
    }

    return [int64]0
}

function Get-ShellItemModifiedDate {
    param([object]$Item)

    try {
        $extendedDate = $Item.ExtendedProperty('System.DateModified')
        if ($extendedDate) {
            $parsedExtendedDate = [datetime]$extendedDate
            if ($parsedExtendedDate.Year -gt 1900) {
                return $parsedExtendedDate
            }
        }
    }
    catch {
    }

    try {
        $directDate = [datetime]$Item.ModifyDate
        if ($directDate.Year -gt 1900) {
            return $directDate
        }
    }
    catch {
    }

    return [datetime]'1900-01-01T00:00:00'
}

function Collect-PhotoItems {
    param(
        [object]$Shell,
        [object]$Folder,
        [string]$RelativeRoot
    )

    $result = New-Object System.Collections.Generic.List[object]
    $queue = New-Object System.Collections.Generic.Queue[object]
    $queue.Enqueue(@($Folder, $RelativeRoot))

    $allowedExt = @(".jpg", ".jpeg", ".png", ".heic", ".heif", ".dng", ".nef", ".raw", ".arw", ".cr2", ".cr3", ".bmp", ".tif", ".tiff", ".mp4", ".mov")

    while ($queue.Count -gt 0) {
        $tuple = $queue.Dequeue()
        $currentFolder = $tuple[0]
        $baseRel = $tuple[1]

        foreach ($item in @($currentFolder.Items())) {
            if ($item.IsFolder) {
                $nextFolder = Open-ShellFolder -Shell $Shell -Item $item
                if ($nextFolder) {
                    $nextRel = if ([string]::IsNullOrEmpty($baseRel)) { $item.Name } else { "$baseRel\\$($item.Name)" }
                    $queue.Enqueue(@($nextFolder, $nextRel))
                }
                continue
            }

            $ext = [System.IO.Path]::GetExtension($item.Name).ToLowerInvariant()
            if (-not ($allowedExt -contains $ext)) {
                continue
            }

            $relPath = if ([string]::IsNullOrEmpty($baseRel)) { $item.Name } else { "$baseRel\\$($item.Name)" }
            $modified = Get-ShellItemModifiedDate -Item $item
            $size = Get-ShellItemSizeBytes -Item $item
            $key = Get-FileKey -RelativePath $relPath -Size $size -Modified $modified

            $result.Add([pscustomobject]@{
                RelativePath = $relPath
                RelativeDir = [System.IO.Path]::GetDirectoryName($relPath)
                Name = $item.Name
                Size = $size
                Modified = $modified
                Key = $key
                SourceFolder = $currentFolder
                SourceItem = $item
            })
        }
    }

    return $result
}

function Ensure-Folder {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Wait-ForFileReady {
    param(
        [string]$Path,
        [int64]$ExpectedSize,
        [int]$TimeoutSeconds
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (Test-Path -LiteralPath $Path) {
            try {
                $actualSize = (Get-Item -LiteralPath $Path).Length
                if ($actualSize -eq $ExpectedSize) {
                    return $true
                }
            }
            catch {
                # Keep polling until file is unlocked and size is stable.
            }
        }
        Start-Sleep -Milliseconds 400
    }

    return $false
}

function Get-SourceFolderSubPathForFile {
    param(
        [string]$BaseSourceSubPath,
        [object]$File
    )

    if ([string]::IsNullOrWhiteSpace($File.RelativeDir)) {
        return $BaseSourceSubPath
    }

    return "$BaseSourceSubPath\$($File.RelativeDir)"
}

function Test-SourceItemPresent {
    param(
        [object]$Shell,
        [object]$DeviceFolder,
        [string]$BaseSourceSubPath,
        [object]$File
    )

    try {
        $folderSubPath = Get-SourceFolderSubPathForFile -BaseSourceSubPath $BaseSourceSubPath -File $File
        $folder = Resolve-SourceFolder -Shell $Shell -DeviceFolder $DeviceFolder -SubPath $folderSubPath
    }
    catch {
        return $false
    }

    foreach ($item in @($folder.Items())) {
        if ($item.IsFolder) {
            continue
        }

        if ($item.Name -ne $File.Name) {
            continue
        }

        $itemSize = Get-ShellItemSizeBytes -Item $item
        if ([int64]$File.Size -le 0 -or $itemSize -eq [int64]$File.Size) {
            return $true
        }
    }

    return $false
}

function Wait-ForSourceItemGone {
    param(
        [object]$Shell,
        [object]$DeviceFolder,
        [string]$BaseSourceSubPath,
        [object]$File,
        [int]$TimeoutSeconds
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (-not (Test-SourceItemPresent -Shell $Shell -DeviceFolder $DeviceFolder -BaseSourceSubPath $BaseSourceSubPath -File $File)) {
            return $true
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Get-DeleteVerbName {
    param([object]$Item)

    $verbs = $Item.Verbs() | ForEach-Object { $_ }
    foreach ($verb in $verbs) {
        $displayName = [string]$verb.Name
        $normalized = ($displayName -replace '&', '').Trim()
        if ($normalized -like '删除*' -or $normalized -ieq 'Delete') {
            return $displayName
        }
    }

    return $null
}

function Remove-SourceItem {
    param(
        [object]$Shell,
        [object]$DeviceFolder,
        [string]$BaseSourceSubPath,
        [object]$File,
        [int]$TimeoutSeconds,
        [switch]$DryRun
    )

    if ($DryRun) {
        Write-Info "[DryRun] Would delete source: $($File.RelativePath)"
        return $true
    }

    if (-not (Test-SourceItemPresent -Shell $Shell -DeviceFolder $DeviceFolder -BaseSourceSubPath $BaseSourceSubPath -File $File)) {
        return $true
    }

    $deleteVerbName = Get-DeleteVerbName -Item $File.SourceItem
    if (-not $deleteVerbName) {
        Write-Info "Delete verb not found for source item: $($File.RelativePath)"
        return $false
    }

    try {
        $File.SourceItem.InvokeVerb($deleteVerbName)
    }
    catch {
        Write-Info "Delete command failed for source item: $($File.RelativePath)"
        return $false
    }

    $removed = Wait-ForSourceItemGone -Shell $Shell -DeviceFolder $DeviceFolder -BaseSourceSubPath $BaseSourceSubPath -File $File -TimeoutSeconds $TimeoutSeconds
    if (-not $removed) {
        Write-Info "Timed out waiting for source deletion: $($File.RelativePath)"
    }

    return $removed
}

function Build-Batches {
    param(
        [object[]]$Files,
        [int]$MaxFiles,
        [int64]$MaxBytes
    )

    $batches = New-Object System.Collections.Generic.List[object]
    $current = New-Object System.Collections.Generic.List[object]
    $currentBytes = [int64]0

    foreach ($f in $Files) {
        $wouldExceedCount = $current.Count -ge $MaxFiles
        $wouldExceedBytes = ($currentBytes + [int64]$f.Size) -gt $MaxBytes

        if ($current.Count -gt 0 -and ($wouldExceedCount -or $wouldExceedBytes)) {
            $batches.Add([pscustomobject]@{
                Files = $current.ToArray()
                TotalBytes = $currentBytes
            })
            $current = New-Object System.Collections.Generic.List[object]
            $currentBytes = [int64]0
        }

        $current.Add($f)
        $currentBytes += [int64]$f.Size
    }

    if ($current.Count -gt 0) {
        $batches.Add([pscustomobject]@{
            Files = $current.ToArray()
            TotalBytes = $currentBytes
        })
    }

    return $batches
}

function Get-BatchFolderPath {
    param(
        [string]$BaseDir,
        [int]$BatchId
    )

    $batchName = "batch_{0:D6}" -f $BatchId
    return (Join-Path $BaseDir $batchName)
}

function Get-ImportedRecordPath {
    param(
        [object]$State,
        [string]$FileKey
    )

    $property = $State.importedFiles.PSObject.Properties[$FileKey]
    if ($property) {
        return [string]$property.Value
    }

    return $null
}

function Remove-ImportedRecord {
    param(
        [object]$State,
        [string]$FileKey
    )

    if ($State.importedFiles.PSObject.Properties[$FileKey]) {
        [void]$State.importedFiles.PSObject.Properties.Remove($FileKey)
    }
}

function Find-ExistingImportedPath {
    param(
        [string]$BaseDir,
        [string]$RelativePath,
        [int64]$ExpectedSize
    )

    $batchFolders = Get-ChildItem -LiteralPath $BaseDir -Directory -Filter "batch_*" -ErrorAction SilentlyContinue | Sort-Object Name
    foreach ($batchFolder in $batchFolders) {
        $candidatePath = Join-Path $batchFolder.FullName $RelativePath
        if (-not (Test-Path -LiteralPath $candidatePath)) {
            continue
        }

        try {
            if ((Get-Item -LiteralPath $candidatePath).Length -eq $ExpectedSize) {
                return $candidatePath
            }
        }
        catch {
        }
    }

    return $null
}

function Main {
    Ensure-Folder -Path $DestinationRoot
    $state = Load-State -BaseDir $DestinationRoot -DevicePattern $DeviceNamePattern -SourcePath $SourceSubPath -DestRoot $DestinationRoot
    $state.devicePattern = $DeviceNamePattern
    $state.sourceSubPath = $SourceSubPath
    $state.destinationRoot = $DestinationRoot
    $resolvedMaxBatchBytes = Resolve-ByteSize -Value $MaxBatchBytes

    Write-Info "Loading shell namespace and device info..."
    $ns = Get-ThisPcFolder
    $device = Find-DeviceFolder -Shell $ns.Shell -ThisPc $ns.ThisPc -Pattern $DeviceNamePattern
    Write-Info "Device found: $($device.Item.Name)"

    $sourceFolder = Resolve-SourceFolder -Shell $ns.Shell -DeviceFolder $device.Folder -SubPath $SourceSubPath
    Write-Info "Scanning media files from source path: $SourceSubPath"

    $allFiles = Collect-PhotoItems -Shell $ns.Shell -Folder $sourceFolder -RelativeRoot ""
    $allFiles = $allFiles | Sort-Object @{ Expression = 'Modified'; Descending = $true }, @{ Expression = 'RelativePath'; Descending = $true }

    if (-not $allFiles -or $allFiles.Count -eq 0) {
        Write-Info "No media files found in source path."
        return
    }

    Write-Info "Found $($allFiles.Count) media files. Building pending list..."

    $pending = New-Object System.Collections.Generic.List[object]
    foreach ($f in $allFiles) {
        $recordedPath = Get-ImportedRecordPath -State $state -FileKey $f.Key
        if ($recordedPath) {
            if ((Test-Path -LiteralPath $recordedPath) -and ((Get-Item -LiteralPath $recordedPath).Length -eq [int64]$f.Size)) {
                if (-not $KeepSourceOnDevice) {
                    [void](Remove-SourceItem -Shell $ns.Shell -DeviceFolder $device.Folder -BaseSourceSubPath $SourceSubPath -File $f -TimeoutSeconds $CopyTimeoutSeconds -DryRun:$DryRun)
                }
                continue
            }

            Remove-ImportedRecord -State $state -FileKey $f.Key
        }

        $existingImportedPath = Find-ExistingImportedPath -BaseDir $DestinationRoot -RelativePath $f.RelativePath -ExpectedSize ([int64]$f.Size)
        if ($existingImportedPath) {
            $state.importedFiles | Add-Member -MemberType NoteProperty -Name $f.Key -Value $existingImportedPath -Force
            if (-not $KeepSourceOnDevice) {
                [void](Remove-SourceItem -Shell $ns.Shell -DeviceFolder $device.Folder -BaseSourceSubPath $SourceSubPath -File $f -TimeoutSeconds $CopyTimeoutSeconds -DryRun:$DryRun)
            }
            continue
        }

        $pending.Add($f)
    }

    Save-State -BaseDir $DestinationRoot -State $state

    if ($pending.Count -eq 0) {
        Write-Info "Nothing pending. All files already imported."
        return
    }

    $batches = Build-Batches -Files $pending.ToArray() -MaxFiles $MaxFilesPerBatch -MaxBytes $resolvedMaxBatchBytes
    Write-Info "Pending files: $($pending.Count). Planned batches: $($batches.Count)."

    $batchOffset = [int]$state.completedBatches.Count

    for ($i = 0; $i -lt $batches.Count; $i++) {
        $batchId = $batchOffset + $i + 1
        $batch = $batches[$i]
        $batchFiles = @($batch.Files)
        $batchRoot = Get-BatchFolderPath -BaseDir $DestinationRoot -BatchId $batchId

        Write-Info "Starting batch #$batchId - files: $($batchFiles.Count), size: $([math]::Round($batch.TotalBytes / 1MB, 2)) MB"

        $batchStarted = Get-Date
        $successCount = 0
        $failedCount = 0

        Ensure-Folder -Path $batchRoot

        foreach ($f in $batchFiles) {
            $destDir = if ([string]::IsNullOrWhiteSpace($f.RelativeDir)) { $batchRoot } else { Join-Path $batchRoot $f.RelativeDir }
            $destPath = Join-Path $batchRoot $f.RelativePath

            Ensure-Folder -Path $destDir

            if ($DryRun) {
                Write-Info "[DryRun] Would copy: $($f.RelativePath)"
                continue
            }

            $recordedPath = Get-ImportedRecordPath -State $state -FileKey $f.Key
            if ($recordedPath) {
                if ((Test-Path -LiteralPath $recordedPath) -and ((Get-Item -LiteralPath $recordedPath).Length -eq [int64]$f.Size)) {
                    continue
                }

                Remove-ImportedRecord -State $state -FileKey $f.Key
            }

            $copied = $false
            for ($retry = 0; $retry -le $MaxRetryPerFile; $retry++) {
                try {
                    if (Test-Path -LiteralPath $destPath) {
                        $existingTarget = Get-Item -LiteralPath $destPath
                        if ($existingTarget.Length -ne [int64]$f.Size) {
                            Remove-Item -LiteralPath $destPath -Force
                        }
                    }

                    $destFolder = $ns.Shell.Namespace($destDir)
                    if (-not $destFolder) {
                        throw "Cannot open destination folder in shell namespace: $destDir"
                    }

                    # 16=NoConfirm, 4=NoProgressBox, 1024=NoErrorUI
                    $destFolder.CopyHere($f.SourceItem, 1044)

                    $ok = Wait-ForFileReady -Path $destPath -ExpectedSize ([int64]$f.Size) -TimeoutSeconds $CopyTimeoutSeconds
                    if ($ok) {
                        $copied = $true
                        break
                    }
                }
                catch {
                    if ($retry -ge $MaxRetryPerFile) {
                        break
                    }
                }
            }

            if ($copied) {
                $state.importedFiles | Add-Member -MemberType NoteProperty -Name $f.Key -Value $destPath -Force
                Save-State -BaseDir $DestinationRoot -State $state
                if (-not $KeepSourceOnDevice) {
                    [void](Remove-SourceItem -Shell $ns.Shell -DeviceFolder $device.Folder -BaseSourceSubPath $SourceSubPath -File $f -TimeoutSeconds $CopyTimeoutSeconds -DryRun:$DryRun)
                }
                $successCount++
            }
            else {
                $failedCount++
                Write-Info "Failed to copy after retries: $($f.RelativePath)"
            }
        }

        if ($DryRun) {
            Write-Info "Batch #$batchId dry-run completed."
            continue
        }

        if ($failedCount -eq 0) {
            $batchEnd = Get-Date
            $state.completedBatches += [pscustomobject]@{
                batchId = $batchId
                batchFolder = $batchRoot
                startedAt = $batchStarted.ToString("o")
                completedAt = $batchEnd.ToString("o")
                fileCount = $batchFiles.Count
                totalBytes = [int64]$batch.TotalBytes
            }
            Save-State -BaseDir $DestinationRoot -State $state
            Write-Info "Batch #$batchId completed successfully."
        }
        else {
            Save-State -BaseDir $DestinationRoot -State $state
            Write-Info "Batch #$batchId partial result - success: $successCount, failed: $failedCount"
        }
    }

    Write-Info "Import process finished."
}

Main
