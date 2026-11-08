import { Environment, Lightformer } from "@react-three/drei";

export function StudioLighting() {
  return (
    <>
      <ambientLight intensity={0.45} />
      <directionalLight
        position={[3, 7, 5]}
        intensity={2.1}
        color="#eef8ff"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0003}
        shadow-camera-left={-5}
        shadow-camera-right={5}
        shadow-camera-top={5}
        shadow-camera-bottom={-5}
      />
      <directionalLight
        position={[-4, 3, -4]}
        intensity={1.4}
        color="#8fc8dc"
      />
      <Environment resolution={128} frames={1}>
        <Lightformer
          form="rect"
          intensity={3}
          position={[0, 5, 0]}
          rotation={[Math.PI / 2, 0, 0]}
          scale={[7, 3, 1]}
          color="#f3f6ff"
        />
        <Lightformer
          form="rect"
          intensity={2}
          position={[-5, 2, 0]}
          rotation={[0, Math.PI / 2, 0]}
          scale={[7, 2, 1]}
          color="#90bcca"
        />
        <Lightformer
          form="rect"
          intensity={2}
          position={[4, 3, 3]}
          rotation={[0, -Math.PI / 3, 0]}
          scale={[5, 2, 1]}
          color="#fff0dc"
        />
      </Environment>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.015, 0]}
        receiveShadow
      >
        <planeGeometry args={[40, 40]} />
        <shadowMaterial transparent opacity={0.32} />
      </mesh>
    </>
  );
}
