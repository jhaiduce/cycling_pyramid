def main():
    with open('/app/production-secrets.ini','w') as fh_ini:
        fh_ini.write('[DEFAULT]\n')
        for secret_name in 'mysql_root_password','mysql_production_password','cycling_admin_password','pyramid_auth_secret':
            with open('/run/secrets/'+secret_name) as fh_secret:
                fh_ini.write('{}:{}\n'.format(secret_name,fh_secret.read()))
