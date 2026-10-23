# airCloud Go 4.3.0 authentication inspection

Inspected on 23 October 2026 for [issue #68](https://github.com/svmironov/aircloud_ha/issues/68).
The APK was supplied locally by the repository owner. It was inspected statically,
without installing/running it or sending account credentials to the cloud.

## Artifact

- File: `airCloud+Go_4.3.0_APKPure.apk`
- Package: `com.jch_hitachi.aircloudglobal`
- `BuildConfig.VERSION_NAME`: `4.3.0`
- `BuildConfig.VERSION_CODE`: `74`
- SHA-256: `28533d6bc5552efe4b7be0d1ab41eaefc15d86145ae3edf108fb55034e1acab1`
- Tool: JADX 1.5.1 (`jadx --no-res -d <output> <apk>`)

JADX reported 52 errors across the full application. The inspected login methods
listed below were emitted without failed-method stubs. This is a source-level
comparison of that path, not a complete audit or a captured network exchange.

## Comparison with the local 4.0.1 sources

| Item | 4.0.1 | 4.3.0 |
| --- | --- | --- |
| API host | `https://api-global-prod.aircloudhome.com` | Same |
| Sign-in | `POST /iam/auth/sign-in` | Same |
| Email request fields | `email`, `password` | Same |
| Phone request field | `mobileNumber` instead of `email` | Same |
| Input normalization | Java `String.trim()` on email and password | Same |
| App request headers | `Content-Type: application/json`, `Accept: application/json` | Same |
| Default OkHttp user agent | `okhttp/4.2.2` | `okhttp/5.3.2` |
| Successful token fields | `token`, `refreshToken`, `type` | Same |
| Refresh | `POST /iam/auth/refresh-token`, refresh bearer token, `isRefreshToken: true` | Same |
| Sign-in error field | `errorState` | Same |

The email sign-in path sends the trimmed password directly in JSON. No new
password hashing/encryption, mandatory app API key, regional host selection,
or CAPTCHA flow was found in that path. The request interceptor can attach an
existing bearer token if one is stored; first sign-in does not require one.

Source locations under the decompiled `sources/` directory:

- `com/jch/racWiFi/BuildConfig.java`: version and host constants.
- `com/jch/racWiFi/userManagement/view/viewImpl/LoginFragment.java`,
  `onClickLogin`: trimming and email/phone selection.
- `com/jch/racWiFi/userManagement/presenter/UserLoginPresenterV2.java`,
  `authenticateUser`: request construction and HTTP status handling.
- `com/jch/racWiFi/userManagement/model/UserLoginDataModel.java`:
  serialized request fields and error constants.
- `com/jch/racWiFi/userManagement/network/UserLoginNetworkDispatcherV2.java`:
  Retrofit sign-in declaration.
- `com/jch/racWiFi/NetworkDispatch/AbstractNetworkDispatcher.java`:
  host, interceptors, headers, refresh authorization.
- `com/jch/racWiFi/di/util/TokenInfo.java`: token field names.
- `okhttp3/internal/_UtilCommonKt.java` and `okhttp3/internal/http/BridgeInterceptor.java`:
  default user-agent value and insertion.

## Implications for issue #68

The supplied 4.3.0 APK does not establish an authentication protocol migration.
The integration previously used a different user agent (`okhttp/4.9.1`), omitted
the explicit JSON Accept header, and passed surrounding whitespace unchanged.
The compatibility patch now aligns these with the inspected application and
closes validation sessions on every exit.

The application distinguishes HTTP 401 with `errorState=UNKNOWN_USER` from other
credential failures; HTTP 403 means an inactive account, 412 an unverified account,
and 423 a soft/hard account lock. The integration now reports these statuses and
logs only recognized error states, never arbitrary error-body fields.

There is no evidence yet that user-agent/header/whitespace differences caused
the reported 401. The next useful evidence is the HTTP status and recognized
`errorState` from one failed sign-in with the updated integration, together with
confirmation of a fresh email/password sign-in in the mobile app. An existing
working app session alone does not exercise a new password sign-in. Offline tests
cannot establish cloud acceptance or resolve an account-specific rejection.
