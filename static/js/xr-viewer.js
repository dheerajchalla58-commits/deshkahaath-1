const dialog = document.getElementById('xrDialog');
if (dialog) {
    const stage = document.getElementById('xrStage');
    const fallbackCard = document.getElementById('xrFallbackCard');
    const fallbackImage = document.getElementById('xrPreviewImage');
    const status = document.getElementById('xrStatus');
    const arButton = document.getElementById('enterAR');
    const vrButton = document.getElementById('enterVR');
    const nameNode = document.getElementById('xrProductName');
    let THREE = null;
    let renderer = null;
    let modelGroup = null;
    let activeSession = null;
    let resizeObserver = null;
    let fallbackPointer = null;

    async function loadThree() {
        if (!THREE) THREE = await import('https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.js');
        return THREE;
    }

    function disposeScene() {
        if (activeSession) activeSession.end().catch(() => {});
        if (resizeObserver) resizeObserver.disconnect();
        if (renderer) {
            renderer.dispose();
            renderer.domElement.remove();
        }
        renderer = null;
        modelGroup = null;
        activeSession = null;
        arButton.disabled = true;
        vrButton.disabled = true;
        stage.classList.remove('has-webgl');
    }

    function makeFrame(imageTexture, width, height) {
        const group = new THREE.Group();
        const metal = new THREE.MeshStandardMaterial({ color: 0x987151, metalness: .72, roughness: .24 });
        const back = new THREE.Mesh(new THREE.BoxGeometry(width + .12, height + .12, .045), metal);
        group.add(back);
        const front = new THREE.Mesh(
            new THREE.PlaneGeometry(width, height),
            new THREE.MeshBasicMaterial({ map: imageTexture, side: THREE.DoubleSide })
        );
        front.position.z = .027;
        group.add(front);
        const glass = new THREE.Mesh(
            new THREE.PlaneGeometry(width + .025, height + .025),
            new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: .07, roughness: .08, metalness: .1, side: THREE.DoubleSide })
        );
        glass.position.z = .03;
        group.add(glass);
        return group;
    }

    async function initPreview(imageUrl, modelUrl = '') {
        disposeScene();
        fallbackCard.hidden = false;
        fallbackImage.src = imageUrl;
        fallbackCard.style.transform = '';
        fallbackPointer = null;
        try {
            await loadThree();
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(36, stage.clientWidth / stage.clientHeight, .1, 40);
            camera.position.set(0, 0, 3.1);
            scene.add(new THREE.HemisphereLight(0xffffff, 0x88684c, 2.2));
            const key = new THREE.DirectionalLight(0xffffff, 2.5);
            key.position.set(-2, 3, 4);
            scene.add(key);
            renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
            renderer.setSize(stage.clientWidth, stage.clientHeight);
            renderer.outputColorSpace = THREE.SRGBColorSpace;
            renderer.xr.enabled = true;
            renderer.xr.setReferenceSpaceType('local');
            stage.append(renderer.domElement);
            stage.classList.add('has-webgl');

            if (modelUrl) {
                status.textContent = 'Loading the craft’s 3D model…';
                const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
                const loader = new GLTFLoader();
                const gltf = await loader.loadAsync(modelUrl, event => {
                    if (event.total) status.textContent = `Loading 3D craft model · ${Math.round(event.loaded / event.total * 100)}%`;
                    else status.textContent = `Loading 3D craft model · ${(event.loaded / (1024 * 1024)).toFixed(1)} MB`;
                });
                const object = gltf.scene;
                const bounds = new THREE.Box3().setFromObject(object);
                const center = bounds.getCenter(new THREE.Vector3());
                const dimensions = bounds.getSize(new THREE.Vector3());
                const largestSide = Math.max(dimensions.x, dimensions.y, dimensions.z) || 1;
                object.position.sub(center);
                object.scale.multiplyScalar(1.35 / largestSide);
                modelGroup = new THREE.Group();
                modelGroup.add(object);
                status.textContent = '3D model ready. On a supported phone or headset, place it in AR or view it in VR.';
            } else {
                const texture = await new THREE.TextureLoader().loadAsync(imageUrl);
                texture.colorSpace = THREE.SRGBColorSpace;
                const ratio = (texture.image?.width || 1) / (texture.image?.height || 1);
                const height = ratio >= 1 ? 1.15 / ratio : 1.15;
                const width = ratio >= 1 ? 1.15 : 1.15 * ratio;
                modelGroup = makeFrame(texture, width, height);
                status.textContent = 'Spatial photo preview ready. On a supported phone or headset, place this image in AR or view it in VR.';
            }
            scene.add(modelGroup);
            fallbackCard.hidden = true;

            const clock = new THREE.Clock();
            const draw = () => {
                if (modelGroup && !renderer.xr.isPresenting) modelGroup.rotation.y = Math.sin(clock.elapsedTime * .45) * .12;
                renderer.render(scene, camera);
            };
            renderer.setAnimationLoop(draw);
            resizeObserver = new ResizeObserver(() => {
                if (!renderer) return;
                camera.aspect = stage.clientWidth / stage.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(stage.clientWidth, stage.clientHeight);
            });
            resizeObserver.observe(stage);
            if (navigator.xr?.isSessionSupported) {
                const [arSupported, vrSupported] = await Promise.all([
                    navigator.xr.isSessionSupported('immersive-ar').catch(() => false),
                    navigator.xr.isSessionSupported('immersive-vr').catch(() => false)
                ]);
                arButton.disabled = !arSupported;
                vrButton.disabled = !vrSupported;
                if (!arSupported && !vrSupported) status.textContent = modelUrl
                    ? 'Interactive 3D model ready. AR and VR need a compatible mobile device or headset.'
                    : 'Spatial photo preview ready. AR and VR need a compatible mobile device or headset.';
            } else {
            status.textContent = modelUrl
                ? 'Interactive 3D model ready. This browser does not expose WebXR; try a compatible mobile browser or headset for AR/VR.'
                : 'Spatial photo preview ready. This browser does not expose WebXR; try a compatible mobile browser or headset for AR/VR.';
            }
        } catch (error) {
            console.warn('3D preview could not load:', error);
            fallbackCard.hidden = false;
            stage.classList.remove('has-webgl');
            status.textContent = '3D preview is shown in a lightweight desktop view. AR/VR needs a browser with WebXR support.';
        }
    }

    async function enterSession(mode) {
        try {
            if (!renderer || !navigator.xr) throw new Error('WebXR is not available in this browser.');
            const sessionType = mode === 'ar' ? 'immersive-ar' : 'immersive-vr';
            const session = await navigator.xr.requestSession(sessionType, {
                requiredFeatures: ['local'],
                optionalFeatures: mode === 'ar' ? ['dom-overlay'] : [],
                ...(mode === 'ar' ? { domOverlay: { root: dialog } } : {})
            });
            activeSession = session;
            await renderer.xr.setSession(session);
            const distance = mode === 'ar' ? -1.4 : -1.8;
            modelGroup.position.set(0, 0, distance);
            modelGroup.rotation.set(0, 0, 0);
            session.addEventListener('end', () => {
                activeSession = null;
                status.textContent = 'Spatial preview ended. You can return to the 3D view.';
            }, { once: true });
        } catch (error) {
            status.textContent = error.name === 'NotAllowedError'
                ? 'The browser could not start this session. Allow camera or headset access and try again.'
                : 'AR/VR could not start on this device. The 3D preview is still available here.';
        }
    }

    document.addEventListener('click', async event => {
        const button = event.target.closest('[data-spatial-view]');
        if (!button) return;
            nameNode.textContent = button.dataset.name || 'Craft preview';
            status.textContent = 'Loading the spatial preview…';
            dialog.showModal();
            await initPreview(button.dataset.image, button.dataset.model || '');
    });
    arButton.addEventListener('click', () => enterSession('ar'));
    vrButton.addEventListener('click', () => enterSession('vr'));
    stage.addEventListener('pointermove', event => {
        if (stage.classList.contains('has-webgl') || fallbackCard.hidden) return;
        const box = stage.getBoundingClientRect();
        const x = (event.clientX - box.left) / box.width - .5;
        const y = (event.clientY - box.top) / box.height - .5;
        fallbackPointer = `perspective(900px) rotateY(${x * 18}deg) rotateX(${-y * 12}deg)`;
        fallbackCard.style.transform = fallbackPointer;
    });
    stage.addEventListener('pointerleave', () => { if (!stage.classList.contains('has-webgl')) fallbackCard.style.transform = ''; });
    dialog.addEventListener('close', disposeScene);
}
