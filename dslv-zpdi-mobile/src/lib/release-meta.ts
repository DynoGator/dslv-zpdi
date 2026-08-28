export const RELEASE = {
  version: "5.7.0",
  versionCode: 570,
  packageId: "labs.dynogator.dslvzpdi",
  apk: "DynoGatorLabs-DSLV-ZPDI-5.7.0.apk",
  aab: "DynoGatorLabs-DSLV-ZPDI-5.7.0.aab",
  apkAlias: "DSLV-ZPDI.apk",
  aabAlias: "DSLV-ZPDI.aab",
  apkSha256: "01b39bf2a665940dedc6fcbf3106b7e8864d230d86ff95f06087921fe96f7cc2",
  aabSha256: "af71a9f9019344b18f71eaac82e685121ad3d1a4054794cf9288d37f4e8454af",
  apkBytes: 1719716,
  aabBytes: 1675418,
  signerSha256: "6779d030844096386e02dff6480b836903716fbb3658164515a56831b52f7f6b",
  signerDn: "CN=DynoGator Labs, OU=DSLV-ZPDI, O=Resonant Genesis LLC, L=Penrose, ST=Colorado, C=US",
} as const;

export type ReleaseMeta = typeof RELEASE;
