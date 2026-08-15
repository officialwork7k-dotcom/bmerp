const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const proxy = async ({ request, params, url }) => {
  const target = `${API_BASE}/api/${params.path}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  const response = await fetch(target, {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? void 0 : await request.arrayBuffer(),
    // @ts-expect-error - Node fetch requires this for streaming bodies
    duplex: "half"
  });
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  return new Response(response.body, { status: response.status, headers: responseHeaders });
};
const GET = proxy;
const POST = proxy;
const PATCH = proxy;
const PUT = proxy;
const DELETE = proxy;
export {
  DELETE,
  GET,
  PATCH,
  POST,
  PUT
};
