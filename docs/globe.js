import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.querySelector("#globe-canvas");
const status = document.querySelector("#status");
const presetSelect = document.querySelector("#preset");
const versionSelect = document.querySelector("#version");
const versions = new Map();
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x123c40);
scene.add(new THREE.AmbientLight(0xffffff, 1.15));
const keyLight = new THREE.DirectionalLight(0xffffff, 0.38);
keyLight.position.set(3, 4, 5);
scene.add(keyLight);

const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 20);
const initialCameraPosition = new THREE.Vector3(0, 0, 3.1);
camera.position.copy(initialCameraPosition);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.minDistance = 1.35;
controls.maxDistance = 6;
controls.target.set(0, 0, 0);
controls.saveState();

const finishedGroup = new THREE.Group();
const goreGroup = new THREE.Group();
const seamGroup = new THREE.Group();
const cutGroup = new THREE.Group();
const overlapGroup = new THREE.Group();
const equatorGroup = new THREE.Group();
const poleZoneGroup = new THREE.Group();
scene.add(
  finishedGroup,
  goreGroup,
  seamGroup,
  cutGroup,
  overlapGroup,
  equatorGroup,
  poleZoneGroup,
);
const previewGroups = [
  finishedGroup,
  goreGroup,
  seamGroup,
  cutGroup,
  overlapGroup,
  equatorGroup,
  poleZoneGroup,
];
const presets = new Map();
let activeMode = "finished";
let presetIndexUrl;
let loadSequence = 0;
const revision = new URL(import.meta.url).searchParams.get("v");

function versionedUrl(path, base) {
  const url = new URL(path, base);
  if (revision) url.searchParams.set("v", revision);
  return url;
}

function setStatus(message) {
  status.textContent = message;
  status.hidden = !message;
}

function resized() {
  const { width, height } = canvas.getBoundingClientRect();
  if (width === 0 || height === 0) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

new ResizeObserver(resized).observe(canvas.parentElement);
window.addEventListener("resize", resized);
resized();

function addSphereVertex(positions, uvs, latitude, longitude, u, v) {
  const cosine = Math.cos(latitude);
  positions.push(cosine * Math.sin(longitude), Math.sin(latitude), cosine * Math.cos(longitude));
  uvs.push(u, v);
}

function buildFinishedGeometry(longitudeSegments = 160, latitudeSegments = 96) {
  const positions = [];
  const uvs = [];
  const indices = [];
  for (let row = 0; row <= latitudeSegments; row += 1) {
    const latitudeFraction = row / latitudeSegments;
    const latitude = Math.PI / 2 - Math.PI * latitudeFraction;
    for (let column = 0; column <= longitudeSegments; column += 1) {
      const longitudeFraction = column / longitudeSegments;
      addSphereVertex(
        positions,
        uvs,
        latitude,
        2 * Math.PI * longitudeFraction,
        longitudeFraction,
        1 - latitudeFraction,
      );
    }
  }
  const stride = longitudeSegments + 1;
  for (let row = 0; row < latitudeSegments; row += 1) {
    for (let column = 0; column < longitudeSegments; column += 1) {
      const start = row * stride + column;
      indices.push(start, start + stride, start + 1, start + 1, start + stride, start + stride + 1);
    }
  }
  return geometryFromData({ positions, uvs, indices });
}

function geometryFromData(data, scale = 1) {
  const geometry = new THREE.BufferGeometry();
  const positions = Float32Array.from(data.positions, (value) => value * scale);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  if (data.uvs) geometry.setAttribute("uv", new THREE.BufferAttribute(Float32Array.from(data.uvs), 2));
  if (data.indices) geometry.setIndex(data.indices);
  geometry.computeVertexNormals();
  return geometry;
}

function lineFromData(positions, color, closed = false) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(Float32Array.from(positions, (value) => value * 1.006), 3),
  );
  return closed
    ? new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color }))
    : new THREE.Line(geometry, new THREE.LineBasicMaterial({ color }));
}

function latitudeRing(latitude, color) {
  const positions = [];
  for (let step = 0; step < 192; step += 1) {
    const longitude = (2 * Math.PI * step) / 192;
    addSphereVertex(positions, [], latitude, longitude, 0, 0);
  }
  return lineFromData(positions, color, true);
}

function disposeObject(object) {
  object.traverse((child) => {
    child.geometry?.dispose();
    const materials = child.material
      ? Array.isArray(child.material) ? child.material : [child.material]
      : [];
    for (const material of materials) {
      material.map?.dispose();
      material.dispose();
    }
  });
}

function clearPreview() {
  for (const group of previewGroups) {
    for (const child of [...group.children]) {
      group.remove(child);
      disposeObject(child);
    }
  }
}

async function loadTexture(url) {
  const texture = await new THREE.TextureLoader().loadAsync(url);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return texture;
}

function setMode(mode) {
  activeMode = mode;
  finishedGroup.visible = mode === "finished";
  goreGroup.visible = mode === "gores";
  for (const button of document.querySelectorAll(".mode-button")) {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}

function setView(view) {
  // Flush pending orbit inertia before choosing an exact camera pose.
  // OrbitControls.reset() restores position but retains its damped deltas.
  const damping = controls.enableDamping;
  const autoRotate = controls.autoRotate;
  controls.enableDamping = false;
  controls.autoRotate = false;
  controls.update();
  if (view === "reset") {
    controls.reset();
  } else {
    const positions = {
      front: [0, 0, 3.1],
      back: [0, 0, -3.1],
      north: [0, 3.1, 0],
      south: [0, -3.1, 0],
    };
    camera.position.fromArray(positions[view]);
    controls.target.set(0, 0, 0);
    controls.update();
  }
  controls.enableDamping = damping;
  controls.autoRotate = autoRotate;
}

function connectControls() {
  versionSelect.addEventListener("change", () => loadVersion());
  presetSelect.addEventListener("change", () => {
    loadPreset(presets.get(presetSelect.value));
  });
  for (const button of document.querySelectorAll(".mode-button")) {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  }
  for (const button of document.querySelectorAll("[data-view]")) {
    button.addEventListener("click", () => setView(button.dataset.view));
  }
  const overlays = [
    ["toggle-seams", seamGroup],
    ["toggle-cuts", cutGroup],
    ["toggle-overlap", overlapGroup],
    ["toggle-equator", equatorGroup],
    ["toggle-poles", poleZoneGroup],
  ];
  for (const [id, group] of overlays) {
    const input = document.querySelector(`#${id}`);
    input.addEventListener("change", () => {
      group.visible = input.checked;
    });
    group.visible = input.checked;
  }
  const autoRotate = document.querySelector("#toggle-rotate");
  autoRotate.addEventListener("change", () => {
    controls.autoRotate = autoRotate.checked;
  });
}

async function loadPreset(entry) {
  if (!entry) return;
  const request = ++loadSequence;
  const selectedVersion = versionSelect.value;
  const textures = [];
  setStatus(`Loading ${entry.label}...`);
  try {
    const manifestUrl = versionedUrl(entry.manifest, presetIndexUrl);
    const response = await fetch(manifestUrl);
    if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);
    const manifest = await response.json();
    const assetUrl = (path) => versionedUrl(path, manifestUrl).href;
    const results = await Promise.allSettled(
      [manifest.texture, ...manifest.gores.map((gore) => gore.texture)].map(async (path) => {
        const texture = await loadTexture(assetUrl(path));
        textures.push(texture);
        return texture;
      }),
    );
    const failure = results.find((result) => result.status === "rejected");
    if (failure) throw failure.reason;
    const [finishedTexture, ...goreTextures] = results.map((result) => result.value);
    if (request !== loadSequence) {
      finishedTexture.dispose();
      for (const texture of goreTextures) texture.dispose();
      return;
    }
    clearPreview();
    finishedGroup.add(
      new THREE.Mesh(
        buildFinishedGeometry(),
        new THREE.MeshLambertMaterial({ map: finishedTexture }),
      ),
    );
    for (const [index, gore] of manifest.gores.entries()) {
      goreGroup.add(
        new THREE.Mesh(
          geometryFromData(gore.mesh),
          new THREE.MeshLambertMaterial({ map: goreTextures[index], side: THREE.DoubleSide }),
        ),
      );
      seamGroup.add(lineFromData(gore.nominal_seam, 0xf6d365));
      cutGroup.add(lineFromData(gore.cut_outline, 0x26393a, true));
      overlapGroup.add(
        new THREE.Mesh(
          geometryFromData(gore.overlap_mesh, 1.003),
          new THREE.MeshBasicMaterial({
            color: 0xc75245,
            transparent: true,
            opacity: 0.36,
            side: THREE.DoubleSide,
            depthWrite: false,
          }),
        ),
      );
    }
    equatorGroup.add(latitudeRing(0, 0x76d5d1));
    const poleLatitude = Math.PI / 2 - (2 * manifest.pole_safety_zone_mm) / manifest.diameter_mm;
    poleZoneGroup.add(latitudeRing(poleLatitude, 0xd37b59));
    poleZoneGroup.add(latitudeRing(-poleLatitude, 0xd37b59));
    setMode(activeMode);
    document.querySelector("#variant-description").textContent = entry.description || "";
    canvas.dataset.variant = entry.id;
    canvas.dataset.version = selectedVersion;
    const version = versions.get(selectedVersion);
    const description = document.querySelector("#version-description");
    description.replaceChildren(document.createTextNode(`${version.description} `));
    if (/^[a-f0-9]{40}$/.test(version.revision)) {
      const link = document.createElement("a");
      link.href = `https://github.com/ehonda/leipzig-globe/commit/${version.revision}`;
      link.textContent = version.revision.slice(0, 7);
      description.append(link);
    }
    setStatus("");
  } catch (error) {
    for (const texture of textures) texture.dispose();
    if (request !== loadSequence) return;
    console.error(error);
    setStatus("Selected preview unavailable. The previous view is still shown; choose a version to retry.");
  }
}

async function loadVersion() {
  const request = ++loadSequence;
  const selectedVersion = versionSelect.value;
  const previousPreset = presetSelect.value;
  setStatus("Loading version...");
  presetSelect.disabled = true;
  try {
    const indexUrl = versionedUrl(versions.get(selectedVersion).index, import.meta.url);
    const response = await fetch(indexUrl);
    if (!response.ok) throw new Error(`Preset request failed: ${response.status}`);
    const index = await response.json();
    if (request !== loadSequence) return;
    if (!Array.isArray(index.presets) || index.presets.length === 0) {
      throw new Error("The preview has no exported presets.");
    }
    presets.clear();
    presetSelect.replaceChildren();
    presetIndexUrl = indexUrl;
    for (const entry of index.presets) {
      if (!entry.id || !entry.label || !entry.manifest) continue;
      presets.set(entry.id, entry);
      presetSelect.add(new Option(entry.label, entry.id));
    }
    if (presets.size === 0) throw new Error("The preview has no valid presets.");
    presetSelect.replaceChildren(...[...presetSelect.options].filter((option) => option.value));
    presetSelect.disabled = false;
    if (presets.has(previousPreset)) presetSelect.value = previousPreset;
    await loadPreset(presets.get(presetSelect.value));
  } catch (error) {
    if (request !== loadSequence) return;
    console.error(error);
    setStatus("Preview presets are unavailable.");
  }
}

async function initialize() {
  try {
    const response = await fetch(versionedUrl("versions.json", import.meta.url));
    if (!response.ok) throw new Error(`Version request failed: ${response.status}`);
    const index = await response.json();
    for (const entry of index.versions) {
      versions.set(entry.id, entry);
      versionSelect.add(new Option(entry.label, entry.id));
    }
    versionSelect.disabled = false;
    await loadVersion();
  } catch (error) {
    console.error(error);
    setStatus("Preview versions are unavailable. Reload to retry.");
  }
}

function render() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}

connectControls();
initialize();
render();
