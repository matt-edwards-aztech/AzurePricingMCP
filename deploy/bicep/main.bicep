@description('The name of the web app')
param appName string = 'azure-pricing-mcp'

@description('The location of the resources')
param location string = resourceGroup().location

@description('The SKU of the App Service plan')
@allowed([
  'F1'
  'D1'
  'B1'
  'B2'
  'B3'
  'S1'
  'S2'
  'S3'
  'P1'
  'P2'
  'P3'
])
param sku string = 'B1'

@description('The runtime stack for the web app')
param linuxFxVersion string = 'PYTHON|3.11'

var appServicePlanName = '${appName}-plan'
var webAppName = appName

resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: sku
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: linuxFxVersion
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'PYTHON_ENABLE_GUNICORN_MULTIWORKERS'
          value: 'true'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'AZURE_API_TIMEOUT'
          value: '30'
        }
      ]
      alwaysOn: sku != 'F1' && sku != 'D1'
      healthCheckPath: '/health'
    }
    httpsOnly: true
  }
}

output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output webAppName string = webApp.name