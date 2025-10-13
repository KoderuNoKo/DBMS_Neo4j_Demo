$base = ".\01_MRI_Data"
$baseUrl  = "http://localhost:8000/01_MRI_Data"  # Change if server URL differs

# CSV output files
$studyCsv        = ".\mri_export\Study.csv"
$seriesCsv       = ".\mri_export\Series.csv"
$imageCsv        = ".\mri_export\Image.csv"
$patientStudyCsv = ".\mri_export\Patient_Study.csv"
$studySeriesCsv  = ".\mri_export\Study_Series.csv"
$seriesImageCsv  = ".\mri_export\Series_Image.csv"

# Clear old CSVs
Remove-Item $studyCsv, $seriesCsv, $imageCsv, $patientStudyCsv, $studySeriesCsv, $seriesImageCsv -ErrorAction SilentlyContinue

# Write headers
"StudyID,Region,Protocol,DateTime,UID" | Out-File $studyCsv
"SeriesID,Name,StudyID" | Out-File $seriesCsv
"ImageID,Filename,Path,SeriesID" | Out-File $imageCsv
"PatientID,StudyID" | Out-File $patientStudyCsv
"StudyID,SeriesID" | Out-File $studySeriesCsv
"SeriesID,ImageID" | Out-File $seriesImageCsv

# Initialize counters
$studyCounter  = 1
$seriesCounter = 1
$imageCounter  = 1

# Walk through patients
Get-ChildItem -Path $base -Directory | ForEach-Object {
    $patientId = $_.Name
    $patientPath = $_.FullName

    # Walk through studies
    Get-ChildItem $patientPath -Directory | ForEach-Object {
        $studyId    = $studyCounter++
        $studyName  = $_.Name   
        $studyParts = $studyName -split "_"

        # Extract Region
        $region = $studyParts[0]

        # Find date (8-digit number like 20160309)
        $dateIndex = ($studyParts | Where-Object { $_ -match '^\d{8}$' } | ForEach-Object { [array]::IndexOf($studyParts, $_) })
        if ($dateIndex -eq $null) { $dateIndex = 2 }

        # Protocol is everything between region and date
        $protocol = ($studyParts[1..($dateIndex-1)] -join "_")

        $rawDate = $studyParts[$dateIndex]
        $rawTime = $studyParts[$dateIndex + 1]
        $uid     = $studyParts[-1]

        # Convert Date+Time into ISO format
        try {
            $dateObj = [datetime]::ParseExact("$rawDate$rawTime", "yyyyMMddHHmmss", $null)
            $dateTimeIso = $dateObj.ToString("yyyy-MM-ddTHH:mm:ss")
        } catch {
            $dateTimeIso = ""
        }

        # Write study and patient-study link
        "$studyId,$region,$protocol,$dateTimeIso,$uid" | Out-File $studyCsv -Append
        "$patientId,$studyId" | Out-File $patientStudyCsv -Append

        # Walk through series
        Get-ChildItem $_.FullName -Directory | ForEach-Object {
            $seriesId   = $seriesCounter++
            $seriesName = $_.Name

            "$seriesId,$seriesName,$studyId" | Out-File $seriesCsv -Append
            "$studyId,$seriesId" | Out-File $studySeriesCsv -Append

            # Walk through images
            Get-ChildItem $_.FullName -File | ForEach-Object {
                $imageId = $imageCounter++
                $fname   = $_.Name
                $fpath   = $_.FullName

                # Build relative path and turn into URL
                $relPath = $fpath.Substring($base.Length).TrimStart('\') -replace '\\','/'
                $url     = "$baseUrl/$relPath"

                "$imageId,$fname,$url,$seriesId" | Out-File $imageCsv -Append
                "$seriesId,$imageId" | Out-File $seriesImageCsv -Append
            }
        }
    }
}
