import msal

from components.environment import CLIENT_ID, CLIENT_SECRET, TENANT_ID


def azure_token():
    scope = ["https://graph.microsoft.com/.default"]
    client = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=f"https://login.microsoftonline.com/{TENANT_ID}", client_credential=CLIENT_SECRET
    )
    token_result = client.acquire_token_silent(scope, account=None)

    if token_result:
        try:
            access_token = f'Bearer {token_result.get("access_token")}'
            print("Access token was loaded from cache")
        except Exception as err:
            print(f"Error while loading access token from cache. Error: {err}")
            return None
            
    else:
        try:
            token_result = client.acquire_token_for_client(scopes=scope)
            access_token = f'Bearer {token_result.get("access_token")}'
            print("New access token was acquired from Azure AD")
        except Exception as err:
            print(f"Error while acquiring new access token from Azure AD. Error: {err}")
            return None
        

    return access_token
