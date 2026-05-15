#!/usr/bin/env node
/**
 * rotate_ply.js — 3DGS PLY rotator (X axis, -90°)
 *
 * Usage:  node rotate_ply.js <input.ply> <output.ply>
 *
 * What it does:
 *   Reads a 3D Gaussian Splatting PLY (binary_little_endian) and writes
 *   the same data with every splat rotated -90° around the world X axis.
 *
 *   Rotated fields:
 *     - position    (x, y, z)
 *     - normals     (nx, ny, nz)  — if present
 *     - splat rotation quaternion (rot_0=w, rot_1=x, rot_2=y, rot_3=z)
 *
 *   NOT rotated:
 *     - scale_0..2  (axis-aligned in the splat's local frame; already
 *                    covered by the rotation quaternion)
 *     - opacity     (scalar)
 *     - f_dc_0..2   (degree-0 SH; rotation-invariant)
 *     - f_rest_*    (degree-1+ SH; would need Wigner D-matrices. We
 *                    print a warning if these are non-zero — most demo
 *                    PLYs have maxSh=0 so f_rest_* aren't even emitted)
 *
 * Why a Node script? The tool chain already requires Node (npm), so
 * adding Python+pip just for this one preprocessing step would balloon
 * the setup cost. Plain fs/Buffer is enough.
 */

const fs = require('fs');
const path = require('path');

const ROT_X_DEG = -90; // hard-coded per project requirement
const ROT_X_RAD = ROT_X_DEG * Math.PI / 180;
// Half-angle quaternion for X-axis rotation:
//   q = (cos(θ/2), sin(θ/2)*1, 0, 0)
const HALF = ROT_X_RAD / 2;
const QW = Math.cos(HALF);
const QX = Math.sin(HALF);
const QY = 0;
const QZ = 0;

// Rotation matrix for the same rotation. With θ = -π/2:
//   [1  0  0]
//   [0  0  1]
//   [0 -1  0]
// So:  x' = x, y' = z, z' = -y
function rotateVec3(x, y, z) {
  return [x, z, -y];
}

// Pre-multiply quaternion: new_q = Q_rot * old_q
// All quaternions are (w, x, y, z).
function preMulQuat(w2, x2, y2, z2) {
  return [
    QW*w2 - QX*x2 - QY*y2 - QZ*z2,
    QW*x2 + QX*w2 + QY*z2 - QZ*y2,
    QW*y2 - QX*z2 + QY*w2 + QZ*x2,
    QW*z2 + QX*y2 - QY*x2 + QZ*w2,
  ];
}

function fail(msg) {
  console.error('[rotate_ply] ' + msg);
  process.exit(1);
}

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) {
  fail('Usage: node rotate_ply.js <input.ply> <output.ply>');
}
if (!fs.existsSync(inPath)) fail('Input file not found: ' + inPath);

const buf = fs.readFileSync(inPath);

// ── 1. Parse PLY header (ASCII until "end_header\n") ──
let headerEnd = buf.indexOf(Buffer.from('end_header\n', 'ascii'));
if (headerEnd < 0) fail('Not a valid PLY (no end_header marker)');
headerEnd += 'end_header\n'.length;
const headerText = buf.subarray(0, headerEnd).toString('ascii');

// Find format
if (!/format\s+binary_little_endian/i.test(headerText)) {
  fail('Only binary_little_endian PLY supported (got: ' + headerText.match(/format[^\n]+/i) + ')');
}

// Find vertex element + count
const vertexMatch = headerText.match(/element\s+vertex\s+(\d+)/i);
if (!vertexMatch) fail('No "element vertex" in PLY header');
const numVertices = parseInt(vertexMatch[1], 10);

// Collect vertex property names+types, IN ORDER (PLY layout depends on it).
// We don't support 'list' properties on vertex (3DGS PLYs don't use them).
// Type sizes: float/float32=4, double=8, char/uchar/int8/uint8=1,
//             short/ushort/int16/uint16=2, int/uint/int32/uint32=4.
const typeSize = {
  char: 1, uchar: 1, int8: 1, uint8: 1,
  short: 2, ushort: 2, int16: 2, uint16: 2,
  int: 4, uint: 4, int32: 4, uint32: 4,
  float: 4, float32: 4,
  double: 8, float64: 8,
};
// Walk header line by line, only within the vertex element scope.
const lines = headerText.split('\n');
const props = []; // [{name, type, offset, size}]
let inVertex = false, stride = 0;
for (const ln of lines) {
  const trimmed = ln.trim();
  if (/^element\s+vertex\s+/i.test(trimmed)) { inVertex = true; continue; }
  if (/^element\s+/i.test(trimmed)) { inVertex = false; continue; }
  if (!inVertex) continue;
  const m = trimmed.match(/^property\s+(\w+)\s+(\w+)\s*$/i);
  if (!m) continue;
  const [, type, name] = m;
  const sz = typeSize[type.toLowerCase()];
  if (sz === undefined) fail('Unsupported PLY property type: ' + type);
  props.push({ name, type: type.toLowerCase(), offset: stride, size: sz });
  stride += sz;
}
if (!props.length) fail('No vertex properties parsed');

// Sanity: file size matches numVertices * stride
const dataBytes = buf.length - headerEnd;
const expected = numVertices * stride;
if (dataBytes !== expected) {
  // Some PLY writers add a trailing newline. Tolerate +/- a few bytes.
  if (Math.abs(dataBytes - expected) > 16) {
    fail(`PLY data section size mismatch: got ${dataBytes}, expected ${expected} (= ${numVertices} vertices × ${stride} bytes/vertex)`);
  }
}

// ── 2. Look up the properties we care about ──
const byName = {};
for (const p of props) byName[p.name] = p;

const need = (n) => {
  const p = byName[n];
  if (!p) return null;
  if (p.type !== 'float' && p.type !== 'float32') {
    console.warn(`[rotate_ply] WARNING: property "${n}" is ${p.type}, expected float32 — skipping`);
    return null;
  }
  return p;
};

const px = need('x'), py = need('y'), pz = need('z');
if (!px || !py || !pz) fail('PLY missing x/y/z float properties');

const nxP = need('nx'), nyP = need('ny'), nzP = need('nz');

const r0 = need('rot_0'), r1 = need('rot_1'), r2 = need('rot_2'), r3 = need('rot_3');
const has3DGSQuat = !!(r0 && r1 && r2 && r3);

// Higher-order SH presence (for warning only)
const restCount = props.filter(p => p.name.startsWith('f_rest_')).length;
if (restCount > 0) {
  console.warn(`[rotate_ply] WARNING: ${restCount} higher-order SH coefficients (f_rest_*) detected.`);
  console.warn(`[rotate_ply]          These need Wigner-D rotation to remain physically correct under`);
  console.warn(`[rotate_ply]          view rotation. This script does NOT rotate them — view-dependent`);
  console.warn(`[rotate_ply]          shading may look slightly off at glancing angles after conversion.`);
  console.warn(`[rotate_ply]          For demo PLYs with maxSh=0 (no f_rest_* properties) this warning`);
  console.warn(`[rotate_ply]          does not apply.`);
}

// ── 3. Make a writable copy of the data section, walk vertices ──
const out = Buffer.from(buf); // copies the entire file (header included)
const dv = new DataView(out.buffer, out.byteOffset, out.byteLength);

const base = headerEnd;
const LE = true;
const get = (i, p) => dv.getFloat32(base + i * stride + p.offset, LE);
const set = (i, p, v) => dv.setFloat32(base + i * stride + p.offset, v, LE);

for (let i = 0; i < numVertices; i++) {
  // Position
  const x = get(i, px), y = get(i, py), z = get(i, pz);
  const [rx, ry, rz] = rotateVec3(x, y, z);
  set(i, px, rx); set(i, py, ry); set(i, pz, rz);

  // Normals (optional)
  if (nxP && nyP && nzP) {
    const nx = get(i, nxP), ny = get(i, nyP), nz = get(i, nzP);
    const [rnx, rny, rnz] = rotateVec3(nx, ny, nz);
    set(i, nxP, rnx); set(i, nyP, rny); set(i, nzP, rnz);
  }

  // 3DGS rotation quaternion (rot_0=w, rot_1=x, rot_2=y, rot_3=z)
  if (has3DGSQuat) {
    const w = get(i, r0), qx = get(i, r1), qy = get(i, r2), qz = get(i, r3);
    const [nw, nx, ny, nz] = preMulQuat(w, qx, qy, qz);
    set(i, r0, nw); set(i, r1, nx); set(i, r2, ny); set(i, r3, nz);
  }
}

// ── 4. Write the rotated PLY ──
fs.writeFileSync(outPath, out);

console.log(`[rotate_ply] OK: rotated ${numVertices.toLocaleString()} vertices by ${ROT_X_DEG}° around X`);
console.log(`[rotate_ply]      input : ${inPath}`);
console.log(`[rotate_ply]      output: ${outPath}`);
