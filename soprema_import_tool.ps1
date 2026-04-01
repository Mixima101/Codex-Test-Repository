Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$templatePath = Join-Path $scriptDir 'Catalog-Import-Template-US.csv'
$defaultMainPagePath = Join-Path $scriptDir 'Products & Systems _ SOPREMA_Main_Product_Listing_Page.html'

$headers = @()
if (Test-Path $templatePath) {
    $headers = (Get-Content -Path $templatePath -TotalCount 1)
    if ($headers.Count -eq 1) {
        $headers = $headers -split ','
    }
}

if (-not $headers -or $headers.Count -eq 0) {
    [System.Windows.Forms.MessageBox]::Show('Could not read template headers from Catalog-Import-Template-US.csv', 'Missing Template', 'OK', 'Error') | Out-Null
    exit 1
}

function Decode-HtmlText {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $noTags = [regex]::Replace($Text, '<[^>]+>', ' ')
    $decoded = [System.Net.WebUtility]::HtmlDecode($noTags)
    return ([regex]::Replace($decoded, '\s+', ' ')).Trim()
}

function Infer-Unit {
    param([string]$RowHtml)
    if ([string]::IsNullOrWhiteSpace($RowHtml)) { return '' }

    $match = [regex]::Match($RowHtml, '/\s*([A-Za-z0-9²]+)\b')
    if ($match.Success) {
        return $match.Groups[1].Value.ToUpperInvariant()
    }
    return ''
}

function Is-LikelyProductUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    $normalized = $Url.Trim()
    if ($normalized.StartsWith('/')) {
        $normalized = "https://www.soprema.ca$normalized"
    }
    $m = [regex]::Match($normalized, '^https?://[^/]+/en/products-systems/([^/?#]+)(?:[/?#].*)?$', 'IgnoreCase')
    return $m.Success
}

function Normalize-ProductUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return '' }
    $normalized = $Url.Trim()
    if ($normalized.StartsWith('/')) {
        $normalized = "https://www.soprema.ca$normalized"
    }
    $normalized = $normalized -replace '[?#].*$', ''
    return $normalized.TrimEnd('/')
}

function Get-ProductLinksFromAlgolia {
    param(
        [string]$ApplicationId,
        [string]$ApiKey,
        [string]$IndexName
    )

    $all = @()
    $page = 0
    $totalPages = 1

    while ($page -lt $totalPages) {
        $bodyObj = @{
            query = ''
            page = $page
            hitsPerPage = 100
        }
        $body = $bodyObj | ConvertTo-Json -Depth 5
        $uri = "https://$ApplicationId-dsn.algolia.net/1/indexes/$IndexName/query"

        $response = Invoke-RestMethod -Method Post -Uri $uri -Headers @{
            'X-Algolia-API-Key' = $ApiKey
            'X-Algolia-Application-Id' = $ApplicationId
        } -ContentType 'application/json' -Body $body -TimeoutSec 60

        if ($null -ne $response.nbPages) {
            $totalPages = [int]$response.nbPages
        }

        foreach ($hit in $response.hits) {
            $u = ''
            if ($hit.PSObject.Properties.Name -contains 'url') { $u = [string]$hit.url }
            elseif ($hit.PSObject.Properties.Name -contains 'product_url') { $u = [string]$hit.product_url }

            if (Is-LikelyProductUrl -Url $u) {
                $all += (Normalize-ProductUrl -Url $u)
            }
        }

        $page++
    }

    return @($all | Sort-Object -Unique)
}

function Get-ProductLinksFromHtml {
    param([string]$Html)

    $matches = [regex]::Matches($Html, 'href\s*=\s*"([^"]*?/en/products-systems/[^"#?]+)"', 'IgnoreCase')
    $urls = @()

    foreach ($m in $matches) {
        $href = $m.Groups[1].Value.Trim()
        if ($href.StartsWith('/')) {
            $href = "https://www.soprema.ca$href"
        }

        if ($href -match '/products-systems/$') { continue }
        if ($href -match '\.(jpg|jpeg|png|svg|pdf)$') { continue }
        if (-not (Is-LikelyProductUrl -Url $href)) { continue }

        $urls += (Normalize-ProductUrl -Url $href)
    }

    # Prefer Algolia pagination when config is present in the HTML, because it includes
    # all "Show more" products from the listing (not just initially rendered links).
    try {
        $appMatch = [regex]::Match($Html, '"applicationId":"([^"]+)"', 'IgnoreCase')
        $keyMatch = [regex]::Match($Html, '"apiKey":"([^"]+)"', 'IgnoreCase')
        $indexMatch = [regex]::Match($Html, '"indexName":"([^"]+)"', 'IgnoreCase')
        if ($appMatch.Success -and $keyMatch.Success -and $indexMatch.Success) {
            $indexName = $indexMatch.Groups[1].Value
            $algoliaLinks = @(Get-ProductLinksFromAlgolia -ApplicationId $appMatch.Groups[1].Value -ApiKey $keyMatch.Groups[1].Value -IndexName $indexName)
            if ($algoliaLinks.Count -eq 0 -and $indexName -notmatch '_products$') {
                $algoliaLinks = @(Get-ProductLinksFromAlgolia -ApplicationId $appMatch.Groups[1].Value -ApiKey $keyMatch.Groups[1].Value -IndexName ($indexName + '_products'))
            }
            if ($algoliaLinks.Count -gt 0) {
                return @($algoliaLinks)
            }
        }
    } catch {
        # Fall back to static link extraction if Algolia query fails.
    }

    return @($urls | Sort-Object -Unique)
}

function Get-ProductsFromPageHtml {
    param(
        [string]$Html,
        [string]$PageUrl
    )

    $products = @()
    $tableMatch = [regex]::Match($Html, '<table[^>]*id="product-line-table"[\s\S]*?<tbody>([\s\S]*?)</tbody>', 'IgnoreCase')
    if (-not $tableMatch.Success) {
        return $products
    }

    $tbody = $tableMatch.Groups[1].Value
    $rowMatches = [regex]::Matches($tbody, '<tr[^>]*class="[^"]*product-line-item[^"]*"[\s\S]*?</tr>', 'IgnoreCase')

    foreach ($row in $rowMatches) {
        $rowHtml = $row.Value
        $nameMatch = [regex]::Match($rowHtml, '<td[^>]*class="[^"]*product-line-product-value[^"]*"[^>]*>([\s\S]*?)</td>', 'IgnoreCase')
        if (-not $nameMatch.Success) { continue }

        $productCell = $nameMatch.Groups[1].Value
        $name = Decode-HtmlText $productCell
        $name = $name -replace 'Product code:\s*\S+',''
        $name = $name.Trim()

        $codeMatch = [regex]::Match($productCell, 'Product code:\s*([A-Za-z0-9\-_]+)', 'IgnoreCase')
        $productCode = if ($codeMatch.Success) { $codeMatch.Groups[1].Value } else { '' }

        $unit = Infer-Unit $rowHtml

        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $products += [PSCustomObject]@{
                Name = $name
                ProductCode = $productCode
                Unit = $unit
                SourcePage = $PageUrl
            }
        }
    }

    return $products
}

function New-ImportRow {
    param(
        [string[]]$Headers,
        [string]$Description,
        [string]$ProductCode,
        [string]$Unit
    )

    $row = [ordered]@{}
    foreach ($h in $Headers) { $row[$h] = '' }

    $row['Part Number'] = 'Soprema'
    $row['Description'] = $Description
    $row['Trade Price'] = '0'
    $row['Cost Price'] = '0'
    $row['Split Price'] = '0'
    $row['Split Cost Price'] = '0'
    $row['Manufacturer'] = 'Soprema'
    $row['Supplier Part Number'] = $ProductCode
    $row['Supplier Description'] = $Description
    $row['Unit of Measurement'] = $Unit

    return [PSCustomObject]$row
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Soprema simPRO Import Builder'
$form.Size = New-Object System.Drawing.Size(760, 430)
$form.StartPosition = 'CenterScreen'

$lblInfo = New-Object System.Windows.Forms.Label
$lblInfo.Location = New-Object System.Drawing.Point(20, 20)
$lblInfo.Size = New-Object System.Drawing.Size(700, 45)
$lblInfo.Text = 'Builds a simPRO import CSV from Soprema product pages. Prices are set to 0, and Part Number is set to Soprema.'
$form.Controls.Add($lblInfo)

$lblUrl = New-Object System.Windows.Forms.Label
$lblUrl.Location = New-Object System.Drawing.Point(20, 74)
$lblUrl.Size = New-Object System.Drawing.Size(160, 20)
$lblUrl.Text = 'Main Products URL:'
$form.Controls.Add($lblUrl)

$txtUrl = New-Object System.Windows.Forms.TextBox
$txtUrl.Location = New-Object System.Drawing.Point(20, 96)
$txtUrl.Size = New-Object System.Drawing.Size(700, 24)
$txtUrl.Text = 'https://www.soprema.ca/en/products-systems'
$form.Controls.Add($txtUrl)

$startButton = New-Object System.Windows.Forms.Button
$startButton.Location = New-Object System.Drawing.Point(20, 138)
$startButton.Size = New-Object System.Drawing.Size(160, 35)
$startButton.Text = 'Start'
$form.Controls.Add($startButton)

$downloadButton = New-Object System.Windows.Forms.Button
$downloadButton.Location = New-Object System.Drawing.Point(194, 138)
$downloadButton.Size = New-Object System.Drawing.Size(160, 35)
$downloadButton.Text = 'Download CSV'
$downloadButton.Enabled = $false
$form.Controls.Add($downloadButton)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(20, 190)
$progress.Size = New-Object System.Drawing.Size(700, 22)
$progress.Minimum = 0
$progress.Maximum = 100
$form.Controls.Add($progress)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 220)
$statusLabel.Size = New-Object System.Drawing.Size(700, 22)
$statusLabel.Text = 'Status: Ready'
$form.Controls.Add($statusLabel)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(20, 250)
$logBox.Size = New-Object System.Drawing.Size(700, 130)
$logBox.Multiline = $true
$logBox.ScrollBars = 'Vertical'
$logBox.ReadOnly = $true
$form.Controls.Add($logBox)

$script:resultRows = @()

function Invoke-Extraction {
    param([string]$SourceUrl)

    $mainHtml = $null
    if (Test-Path $defaultMainPagePath) {
        $mainHtml = Get-Content -Path $defaultMainPagePath -Raw -Encoding UTF8
    } else {
        $mainHtml = (Invoke-WebRequest -Uri $SourceUrl -UseBasicParsing -TimeoutSec 60).Content
    }

    $links = @(Get-ProductLinksFromHtml -Html $mainHtml)
    if ($links.Count -eq 0) {
        throw "No product links found from main page."
    }
    $logBox.AppendText("Discovered $($links.Count) product page URLs.`r`n")
    [System.Windows.Forms.Application]::DoEvents()

    $allProducts = New-Object System.Collections.Generic.List[object]
    $count = $links.Count
    for ($i = 0; $i -lt $count; $i++) {
        $link = $links[$i]
        try {
            $html = (Invoke-WebRequest -Uri $link -UseBasicParsing -TimeoutSec 60).Content
            $products = Get-ProductsFromPageHtml -Html $html -PageUrl $link
            foreach ($p in $products) { [void]$allProducts.Add($p) }
            $msg = "[$($i + 1)/$count] $link -> $($products.Count) rows"
        } catch {
            $msg = "[$($i + 1)/$count] Failed: $link"
        }

        $pct = [Math]::Max(1, [int](($i + 1) * 100 / $count))
        $progress.Value = [Math]::Min(100, [Math]::Max(0, $pct))
        $statusLabel.Text = "Status: Running ($pct%)"
        $logBox.AppendText("$msg`r`n")
        [System.Windows.Forms.Application]::DoEvents()
    }

    $dedup = $allProducts | Group-Object Name, ProductCode | ForEach-Object { $_.Group[0] }
    $rows = foreach ($p in $dedup) {
        New-ImportRow -Headers $headers -Description $p.Name -ProductCode $p.ProductCode -Unit $p.Unit
    }
    return $rows
}

$startButton.Add_Click({
    $startButton.Enabled = $false
    $downloadButton.Enabled = $false
    $progress.Value = 0
    $logBox.Clear()
    $statusLabel.Text = 'Status: Starting...'
    [System.Windows.Forms.Application]::DoEvents()

    try {
        $script:resultRows = Invoke-Extraction -SourceUrl $txtUrl.Text
        $statusLabel.Text = "Status: Complete. Found $($script:resultRows.Count) unique products."
        $progress.Value = 100
        $downloadButton.Enabled = $script:resultRows.Count -gt 0
    } catch {
        $statusLabel.Text = "Status: Error"
        $logBox.AppendText("Error: $($_.Exception.Message)`r`n")
    } finally {
        $startButton.Enabled = $true
    }
})

$downloadButton.Add_Click({
    if (-not $script:resultRows -or $script:resultRows.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show('No results available. Click Start first.', 'No Data', 'OK', 'Information') | Out-Null
        return
    }

    $dialog = New-Object System.Windows.Forms.SaveFileDialog
    $dialog.Filter = 'CSV files (*.csv)|*.csv'
    $dialog.FileName = 'Soprema-simPRO-import.csv'

    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $script:resultRows | Export-Csv -Path $dialog.FileName -NoTypeInformation -Encoding UTF8
        [System.Windows.Forms.MessageBox]::Show("Saved: $($dialog.FileName)", 'Done', 'OK', 'Information') | Out-Null
    }
})

[void]$form.ShowDialog()
