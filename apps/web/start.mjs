// launch.json can't inject env vars into a spawned process, and
// adapter-node's server reads PORT from the environment — this tiny
// wrapper pins it before loading the built server, so `npm run start`
// always serves on the same port the app has been using throughout.
process.env.PORT ??= '5173';
await import('./build/index.js');
