$OutputFile = "PROJECT_CONTEXT_BUNDLE.md"

$ExcludedFolders = @(
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "data",
    "test_documents"
)

$AllowedExtensions = @(
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".txt"
)

$SpecialFiles = @(
    ".gitignore",
    ".env.example"
)

"# CUSTOMS AI CHECKER — PROJECT CONTEXT BUNDLE" | Set-Content $OutputFile -Encoding UTF8
"" | Add-Content $OutputFile

Get-ChildItem -Recurse -File |
    Where-Object {
        $file = $_

        $notExcluded = $true
        foreach ($folder in $ExcludedFolders) {
            if ($file.FullName -match "[\\/]\Q$folder\E[\\/]") {
                $notExcluded = $false
                break
            }
        }

        $allowed =
            ($AllowedExtensions -contains $file.Extension.ToLower()) -or
            ($SpecialFiles -contains $file.Name)

        $notExcluded -and
        $allowed -and
        $file.Name -ne $OutputFile -and
        $file.Name -ne "make_bundle.ps1"
    } |
    Sort-Object FullName |
    ForEach-Object {

        $RelativePath = Resolve-Path -Relative $_.FullName

        "" | Add-Content $OutputFile
        "---" | Add-Content $OutputFile
        "" | Add-Content $OutputFile
        "# FILE: $RelativePath" | Add-Content $OutputFile
        "" | Add-Content $OutputFile
        "---" | Add-Content $OutputFile
        "" | Add-Content $OutputFile

        Get-Content $_.FullName -Raw |
            Add-Content $OutputFile

        "" | Add-Content $OutputFile
    }

Write-Host ""
Write-Host "DONE: $OutputFile"
