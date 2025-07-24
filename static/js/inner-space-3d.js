const {
  useState,
  useEffect,
  useRef
} = React;

// Working 3D Inner Space Component
const InnerSpace = ({
  stories = [],
  onStoryClick
}) => {
  const mountRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  useEffect(() => {
    // Add a small delay to ensure DOM is ready
    const timer = setTimeout(() => {
      if (typeof THREE === 'undefined') {
        console.log('Three.js not available');
        setHasError(true);
        setIsLoading(false);
        return;
      }
      if (!mountRef.current) {
        console.log('Mount ref not available');
        setHasError(true);
        setIsLoading(false);
        return;
      }
      try {
        console.log('Initializing 3D scene...');

        // Create scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0f0f23);

        // Create camera
        const camera = new THREE.PerspectiveCamera(75, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000);
        camera.position.z = 10;

        // Create renderer
        const renderer = new THREE.WebGLRenderer({
          antialias: true
        });
        renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
        renderer.setClearColor(0x0f0f23);

        // Add to DOM
        mountRef.current.appendChild(renderer.domElement);

        // Add OrbitControls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.1;

        // Create multiple story spheres
        const spheres = [];
        const colors = [0x8b5cf6, 0x06b6d4, 0x10b981, 0xf59e0b, 0xef4444, 0xec4899];

        // Create spheres for stories with organic positioning
        for (let i = 0; i < Math.max(4, stories.length); i++) {
          const geometry = new THREE.SphereGeometry(0.4 + Math.random() * 0.4, 16, 16);
          const material = new THREE.MeshBasicMaterial({
            color: colors[i % colors.length],
            transparent: true,
            opacity: 0.7 + Math.random() * 0.3
          });
          const sphere = new THREE.Mesh(geometry, material);

          // More organic, natural positioning
          const baseAngle = i / Math.max(4, stories.length) * Math.PI * 2;
          const angleVariation = (Math.random() - 0.5) * 0.8; // Add randomness to angle
          const radiusVariation = 2.5 + Math.random() * 2; // Vary distance from center
          const heightVariation = (Math.random() - 0.5) * 3; // More height variation

          const finalAngle = baseAngle + angleVariation;
          sphere.position.x = Math.cos(finalAngle) * radiusVariation + (Math.random() - 0.5) * 0.5;
          sphere.position.y = Math.sin(finalAngle) * radiusVariation + (Math.random() - 0.5) * 0.5;
          sphere.position.z = heightVariation + (Math.random() - 0.5) * 1.5;
          scene.add(sphere);
          spheres.push(sphere);
        }

        // Add some stars
        const starGeometry = new THREE.BufferGeometry();
        const starVertices = [];
        for (let i = 0; i < 200; i++) {
          starVertices.push((Math.random() - 0.5) * 50, (Math.random() - 0.5) * 50, (Math.random() - 0.5) * 50);
        }
        starGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starVertices, 3));
        const starMaterial = new THREE.PointsMaterial({
          color: 0xffffff,
          size: 0.1
        });
        const stars = new THREE.Points(starGeometry, starMaterial);
        scene.add(stars);

        // Animation loop
        const animate = () => {
          requestAnimationFrame(animate);

          // Rotate spheres
          spheres.forEach((sphere, index) => {
            sphere.rotation.y += 0.01 + index * 0.002;
            sphere.rotation.x += 0.005;
          });

          // Rotate stars
          stars.rotation.y += 0.0005;
          controls.update();
          renderer.render(scene, camera);
        };
        console.log('Starting animation...');
        animate();
        setIsLoading(false);
        setHasError(false);

        // Cleanup
        return () => {
          if (mountRef.current && renderer.domElement && mountRef.current.contains(renderer.domElement)) {
            mountRef.current.removeChild(renderer.domElement);
          }
          renderer.dispose();
          controls.dispose();
        };
      } catch (error) {
        console.error('3D initialization error:', error);
        setHasError(true);
        setIsLoading(false);
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [stories]);

  // Fallback when 3D fails
  if (hasError) {
    return /*#__PURE__*/React.createElement("div", {
      className: "relative w-full h-64 rounded-xl overflow-hidden bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900"
    }, /*#__PURE__*/React.createElement("div", {
      className: "absolute inset-0 flex items-center justify-center"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-center text-white p-6"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-4xl mb-4"
    }, "\uD83C\uDF0C"), /*#__PURE__*/React.createElement("h3", {
      className: "text-lg font-semibold mb-2"
    }, "Your Inner Space"), /*#__PURE__*/React.createElement("p", {
      className: "text-sm text-purple-200 mb-4"
    }, stories.length, " stories in your space"), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 gap-2 max-w-xs"
    }, stories.slice(0, 4).map((story, index) => /*#__PURE__*/React.createElement("button", {
      key: story.id || index,
      onClick: () => onStoryClick && onStoryClick(story),
      className: "p-2 bg-white/10 rounded-lg text-xs hover:bg-white/20 transition-colors"
    }, "Story ", index + 1))))));
  }
  return /*#__PURE__*/React.createElement("div", {
    className: "relative w-full h-64 rounded-xl overflow-hidden bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900"
  }, isLoading && /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0 flex items-center justify-center text-white z-10"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-center"
  }, /*#__PURE__*/React.createElement("div", {
    className: "animate-spin w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full mb-2 mx-auto"
  }), /*#__PURE__*/React.createElement("p", {
    className: "text-sm"
  }, "Loading your inner space..."))), /*#__PURE__*/React.createElement("div", {
    ref: mountRef,
    className: "w-full h-full"
  }), /*#__PURE__*/React.createElement("div", {
    className: "absolute bottom-2 left-2 text-white text-xs bg-black/30 rounded px-2 py-1 backdrop-blur-sm"
  }, "\uD83C\uDF0C Drag to rotate \u2022 Scroll to zoom"));
};
window.InnerSpace = InnerSpace;