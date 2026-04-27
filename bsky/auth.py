def login(client, handle, app_password):
    resp = client.post('com.atproto.server.createSession', {
        'identifier': handle,
        'password': app_password,
    })
    # accessJwt expires in ~2 hours; we re-auth on each run so no refresh needed
    return resp['accessJwt'], resp['did']
