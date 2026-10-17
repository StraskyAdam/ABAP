$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

# List mode exercises request generation without network access or file writes.
$requests = @(& (Join-Path $PSScriptRoot "download-xsa-json.ps1") -ListRequests)
$scopeRequests = @($requests | Where-Object Name -like "xsa-scope-*")
Assert-True ($requests.Count -eq 325) "Expected 15 non-scope and 310 scope requests"
Assert-True ($scopeRequests.Count -eq 310) "Expected 310 scope requests"
Assert-True (@($requests.Name | Sort-Object -Unique).Count -eq 325) "Duplicate fixture names"
Assert-True (@($scopeRequests.Path | Sort-Object -Unique).Count -eq 310) "Duplicate scope paths"

$scenarios = @(
    @{ Name = "over-service"; Endpoint = "openOwnerPO.xsodata/openPOParameters"; Pstype = "9"; Flow = "over"; Kind = "service" },
    @{ Name = "over-material"; Endpoint = "openOwnerPO.xsodata/openPOParameters"; Pstype = "0"; Flow = "over"; Kind = "material" },
    @{ Name = "under-service"; Endpoint = "thresholdPO.xsodata/thresholdParameters"; Pstype = "9"; Flow = "under"; Kind = "service" },
    @{ Name = "under-material"; Endpoint = "thresholdPO.xsodata/thresholdParameters"; Pstype = "0"; Flow = "under"; Kind = "material" },
    @{ Name = "exclude"; Endpoint = "exclusionPO.xsodata/exclusionPOParameters"; Flow = "exclude" }
)
$unitPath = Join-Path $PSScriptRoot "../ABAP code/Unit test.txt"
$source = Get-Content -LiteralPath $unitPath -Raw

function Get-ClassBlock {
    param([string]$Name, [string]$Kind)
    $blocks = [regex]::Matches($source, "(?ms)^CLASS $Name $Kind\b(?! DEFERRED).*?^ENDCLASS\.")
    Assert-True ($blocks.Count -eq 1) "Expected one $Kind for $Name"
    $blocks[0].Value
}

$scopeClasses = [regex]::Matches($source, '(?m)^CLASS ltc_scope_\w+ DEFINITION FINAL FOR TESTING')
Assert-True ($scopeClasses.Count -eq 5) "Expected exactly five scope test classes"
$helper = Get-ClassBlock "lcl_scope_parity" "IMPLEMENTATION"
Assert-True ($helper.Contains('|xsa-scope-{ i_scenario }-{ i_number }.json|')) "Incorrect shared fixture naming"
Assert-True ($helper.Contains('|xsa-null-{ i_number }@takeda.com|')) "Incorrect shared scope user"
Assert-True ($helper.Contains('lo_parity->run_paged_case( is_case = ls_case )')) "Scope tests must use the parity comparison"
Assert-True ($helper.Contains('lo_parity->assert_no_differences( )')) "Scope tests must assert parity"

foreach ($scenario in $scenarios) {
    $name = $scenario.Name
    $class = "ltc_scope_" + $name.Replace("-", "_")
    $definition = Get-ClassBlock $class "DEFINITION"
    $implementation = Get-ClassBlock $class "IMPLEMENTATION"
    $declarations = [regex]::Matches($definition, 'METHODS (test_scope_\d{2}) FOR TESTING RAISING cx_static_check\.')
    $methods = [regex]::Matches($implementation, 'METHOD (test_scope_\d{2})\.')
    Assert-True ($declarations.Count -eq 62) "$class must declare 62 scope tests"
    Assert-True ($methods.Count -eq 62) "$class must implement 62 scope tests"
    Assert-True ($definition -match 'DURATION LONG\s+RISK LEVEL HARMLESS') "Incorrect runtime category for $class"
    Assert-True ($implementation -match "lcl_scope_parity=>run_case\(\s+i_scenario = '$name' i_number = i_number \)") "Incorrect scenario for $class"
    Assert-True ($helper -match "(?s)WHEN [^.]*'$name'[^.]*\.\s+ls_case-flow = zif_fi_das_dashboard=>mc_$($scenario.Flow)\.") "Incorrect ABAP flow for $name"
    if ($scenario.ContainsKey("Kind")) {
        Assert-True ($helper -match "(?s)WHEN [^.]*'$name'[^.]*\.\s+ls_case-pstype = zif_fi_das_dashboard=>mc_pstype_$($scenario.Kind)\.") "Incorrect ABAP PSTYPE for $name"
    }
    else {
        Assert-True ($helper -notmatch "(?s)WHEN [^.]*'exclude'[^.]*\.\s+ls_case-pstype") "Exclusion must not set PSTYPE"
    }

    foreach ($number in 1..62) {
        $nn = "{0:D2}" -f $number
        $fixture = "xsa-scope-$name-$nn.json"
        $request = @($scopeRequests | Where-Object Name -eq $fixture)
        Assert-True ($request.Count -eq 1) "Missing or duplicate request: $fixture"
        $parameters = "IP_EMAIL='xsa-null-$nn@takeda.com',IP_POOWNER=''"
        if ($scenario.ContainsKey("Pstype")) {
            $parameters = "IP_PSTYPE='$($scenario.Pstype)',$parameters"
        }
        $expectedPath = "/$($scenario.Endpoint)($parameters)/Results"
        Assert-True ($request[0].Path -ceq $expectedPath) "Incorrect endpoint/parameters: $fixture"
        Assert-True ($request[0].PageSize -eq 1000) "Incorrect page size: $fixture"
        Assert-True ($definition.Contains("METHODS test_scope_$nn FOR TESTING")) "Missing declaration: $class scope $nn"
        Assert-True ($implementation -match "METHOD test_scope_$nn\.\s+run_scope_case\( '$nn' \)\.\s+ENDMETHOD\.") "Incorrect scope number: $class scope $nn"
    }

    $identifiers = [regex]::Matches($definition + $implementation, '(?m)^\s*(?:CLASS|METHODS|METHOD)\s+(\w+)')
    foreach ($identifier in $identifiers) {
        Assert-True ($identifier.Groups[1].Value.Length -le 30) "ABAP identifier exceeds 30 characters"
    }
    Write-Host "$class : 62 scope tests and matching fixture requests verified"
}

foreach ($kind in @("DEFINITION", "IMPLEMENTATION")) {
    $gateway = Get-ClassBlock "ltc_fi_das_gateway_parity" $kind
    Assert-True ($gateway -notmatch '\b(test_scope_\d{2}|run_scope_case)\b') "Scope cases remain in Gateway parity $kind"
}

Write-Host "PASS: 310 unique scope requests, five classes x 62 tests, no Gateway scope tests"
