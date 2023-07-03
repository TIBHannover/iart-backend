from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class OIDCAB_USERNAME(OIDCAuthenticationBackend):
    def get_username(self, claims):
        name = claims.get('given_name', '') + ' ' + claims.get('family_name', '')
        name = name.strip()
        if name != '':
            return name
        return claims.get('preferred_username', claims.get('email'))

    def create_user(self, claims):
        user = super(OIDCAB_USERNAME, self).create_user(claims)
        user.is_oidc = True
        user.save()
        return user
