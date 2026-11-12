# Open the study guide in Microsoft Word, fill the table of contents and page fields, save,
# and export a PDF next to it. Windows only; needs Word installed. Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File tools/study_guide/finalize_word.ps1
param([string]$Docx = "build/study_guide/SENTINEL_materi_belajar.docx")
$ErrorActionPreference = "Stop"
$path = (Resolve-Path $Docx).Path
$pdf = [System.IO.Path]::ChangeExtension($path, ".pdf")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($path, $false, $false, $false)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $null = $doc.Fields.Update()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)
    $pages = $doc.ComputeStatistics(2)
    $doc.Close()
    Write-Output "pages=$pages"
    Write-Output "pdf=$pdf"
}
finally {
    try { $word.Quit() } catch { }
    $null = [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
