import { Suspense } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { Center, OrbitControls } from '@react-three/drei'
import { STLLoader } from 'three-stdlib'

function StlMesh({ url }: { url: string }) {
  const geometry = useLoader(STLLoader, url)
  return (
    <mesh geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial color="#9db4cc" metalness={0.15} roughness={0.55} />
    </mesh>
  )
}

export function Viewer3D({ stlUrl }: { stlUrl: string }) {
  return (
    <Canvas camera={{ position: [80, 80, 80], fov: 45 }} shadows>
      <color attach="background" args={['#12161c']} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[120, 180, 120]} intensity={1.1} castShadow />
      <directionalLight position={[-100, 60, -80]} intensity={0.3} />
      <Suspense fallback={null}>
        <Center key={stlUrl}>
          <StlMesh url={stlUrl} />
        </Center>
      </Suspense>
      <gridHelper args={[300, 30, '#2a3340', '#1c232c']} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
    </Canvas>
  )
}
