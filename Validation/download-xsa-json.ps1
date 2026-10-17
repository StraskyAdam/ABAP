param([switch]$ListRequests)

$ErrorActionPreference = "Stop"

$root = "https://edge-accruals-non-prod-dev-accrual-approuter.cfapps.eu10.hana.ondemand.com/comtakedaAccrual_UI5/XSA_HTTP_ACCRUAL/xsodata"
$email = "adam.strasky@takeda.com"

$requests = @(

# All data without owner

    @{
        Name = "xsa-over-material.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='0',IP_EMAIL='$email',IP_POOWNER='')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-over-service.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='9',IP_EMAIL='$email',IP_POOWNER='')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-under-material.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='0',IP_EMAIL='$email',IP_POOWNER='')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-under-service.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='9',IP_EMAIL='$email',IP_POOWNER='')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-exclude.json"
        Path = "/exclusionPO.xsodata/exclusionPOParameters(IP_EMAIL='$email',IP_POOWNER='')/Results"
        PageSize = 1000
    },

# Specific owner

    @{
        Name = "xsa-over-material-owner.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='0',IP_EMAIL='anita.estrada@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-over-service-owner.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='9',IP_EMAIL='elisa.pawlak@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-under-material-owner.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='0',IP_EMAIL='katarina.simic@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-under-service-owner.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='9',IP_EMAIL='teresa.scoggin@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-exclude-owner.json"
        Path = "/exclusionPO.xsodata/exclusionPOParameters(IP_EMAIL='alta.bazile@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },

# Filter for Company code, Cost center & Management unit

    @{
        Name = "xsa-filter.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='9',IP_EMAIL='patricia-tiemi.oshiro@takeda.com',IP_POOWNER='')/Results"
        PageSize = 1000
    },

# Selection via PO number, item & Supplier

    @{
        Name = "xsa-selection.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='9',IP_EMAIL='$email',IP_POOWNER='')/Results?`$filter=PONUMBER eq '8000401022' and ITEMNO eq '00002' and substringof('Fuji',SUPPLIERNAME)"
        PageSize = 1000
    },

# Decimal format

    @{
        Name = "xsa-y_format.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='0',IP_EMAIL='agnieszka.blaszczyk@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-x_format.json"
        Path = "/openOwnerPO.xsodata/openPOParameters(IP_PSTYPE='9',IP_EMAIL='anchalee.chittawut@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    },
    @{
        Name = "xsa-empty_format.json"
        Path = "/thresholdPO.xsodata/thresholdParameters(IP_PSTYPE='0',IP_EMAIL='ana.verdiguel@takeda.com',IP_POOWNER='X')/Results"
        PageSize = 1000
    }
)

# Scope NULL / wildcard matrix: 5 scenarios x 62 scopes = 310 fixtures.
# Users xsa-null-01..62@takeda.com must exist in XSA and ABAP
# with identical COMPANY_CODE / MANAGEMENT_UNIT / COST_CENTER.
# All scenarios use no owner; exclusion has no IP_PSTYPE parameter.
$scopeScenarios = @(
    @{ Name = "over-service"; Endpoint = "openOwnerPO.xsodata/openPOParameters"; Pstype = "9" },
    @{ Name = "over-material"; Endpoint = "openOwnerPO.xsodata/openPOParameters"; Pstype = "0" },
    @{ Name = "under-service"; Endpoint = "thresholdPO.xsodata/thresholdParameters"; Pstype = "9" },
    @{ Name = "under-material"; Endpoint = "thresholdPO.xsodata/thresholdParameters"; Pstype = "0" },
    @{ Name = "exclude"; Endpoint = "exclusionPO.xsodata/exclusionPOParameters" }
)

foreach ($scenario in $scopeScenarios) {
    1..62 | ForEach-Object {
        $number = "{0:D2}" -f $_
        $parameters = "IP_EMAIL='xsa-null-$number@takeda.com',IP_POOWNER=''"
        if ($scenario.ContainsKey("Pstype")) {
            $parameters = "IP_PSTYPE='$($scenario.Pstype)',$parameters"
        }

        $requests += @{
            Name = "xsa-scope-$($scenario.Name)-$number.json"
            Path = "/$($scenario.Endpoint)($parameters)/Results"
            PageSize = 1000
        }
    }
}

if ($ListRequests) {
    $requests
    return
}

function Get-XsaAllPages {
    param(
        [string]$BaseUrl,
        [string]$OutputFile,
        [int]$Top
    )

    $skip = 0
    $allRows = @()

    do {
        $separator = "?"

        if ($BaseUrl.Contains("?")) {
            $separator = "&"
        }

        $url = "$BaseUrl$separator`$format=json&`$skip=$skip&`$top=$Top"

        Write-Host "Downloading $OutputFile : skip=$skip, top=$Top"

        try {
            $response = Invoke-RestMethod `
                -Uri $url `
                -Method Get `
                -UseDefaultCredentials `
                -Headers @{
                    Accept = "application/json"
                }
        }
        catch {
            Write-Host "Failed URL: $url"

            if ($null -ne $_.Exception.Response) {
                $reader = New-Object System.IO.StreamReader(
                    $_.Exception.Response.GetResponseStream()
                )

                Write-Host $reader.ReadToEnd()
                $reader.Close()
            }

            throw
        }

        $rows = @($response.d.results)

        $allRows += $rows
        $skip += $rows.Count
    }
    while ($rows.Count -eq $Top)

    @{
        d = @{
            results = $allRows
        }
    } |
        ConvertTo-Json -Depth 100 |
        Set-Content -Path $OutputFile -Encoding UTF8

    Write-Host "Saved $($allRows.Count) rows to $OutputFile"
}

foreach ($request in $requests) {
    Get-XsaAllPages `
        -BaseUrl "$root$($request.Path)" `
        -OutputFile $request.Name `
        -Top $request.PageSize
}