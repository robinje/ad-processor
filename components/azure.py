import msal

from components.environment import CLIENT_ID, CLIENT_SECRET, RESOURCE, API_VERSION, TOKEN_URL, TENANT_ID


def azure_token():
    scope = ["https://graph.microsoft.com/.default"]
    client = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}", client_credential=CLIENT_SECRET
    )
    token_result = client.acquire_token_silent(scope, account=None)

    if token_result:
        access_token = f'Bearer {token_result["access_token"]}'
        print("Access token was loaded from cache")
    else:
        token_result = client.acquire_token_for_client(scopes=scope)
        access_token = f'Bearer {token_result["access_token"]}'
        print("New access token was acquired from Azure AD")

    return access_token
