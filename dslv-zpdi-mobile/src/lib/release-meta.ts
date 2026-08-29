export const RELEASE = {
  version: "5.8.0",
  versionCode: 580,
  packageId: "labs.dynogator.dslvzpdi",
  apk: "DynoGatorLabs-DSLV-ZPDI-5.8.0.apk",
  aab: "DynoGatorLabs-DSLV-ZPDI-5.8.0.aab",
  apkAlias: "DSLV-ZPDI.apk",
  aabAlias: "DSLV-ZPDI.aab",
  apkSha256: "25036c57a0df01665fb4f6f4d4480943e3da9bf86b25c65f83a0e01e06a7928e",
  aabSha256: "c82d8e6afe5f21c66ea1d1217885cacb8bfd9d08edea49241d93618bd4b47302",
  apkBytes: 1725853,
  aabBytes: 1682870,
  signerSha256: "6779d030844096386e02dff6480b836903716fbb3658164515a56831b52f7f6b",
  signerDn: "CN=DynoGator Labs, OU=DSLV-ZPDI, O=Resonant Genesis LLC, L=Penrose, ST=Colorado, C=US",
} as const;

export type ReleaseMeta = typeof RELEASE;
