import React, { useEffect, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface AvatarProps {
  audioElement: HTMLAudioElement | null;
  isPlaying: boolean;
}

function ProceduralAvatar({ audioElement, isPlaying }: AvatarProps) {
  const headRef = useRef<THREE.Mesh>(null);
  const mouthRef = useRef<THREE.Mesh>(null);
  const analyserRef = useRef<THREE.AudioAnalyser | null>(null);

  useEffect(() => {
    if (!isPlaying || !audioElement) {
      analyserRef.current = null;
      return;
    }
    try {
      const listener = new THREE.AudioListener();
      const audio = new THREE.Audio(listener);
      audio.setMediaElementSource(audioElement);
      analyserRef.current = new THREE.AudioAnalyser(audio, 32);
    } catch {
      analyserRef.current = null;
    }
    return () => { analyserRef.current = null; };
  }, [isPlaying, audioElement]);

  useFrame(({ clock }) => {
    if (!headRef.current || !mouthRef.current) return;

    // Idle breathing bob
    headRef.current.position.y = Math.sin(clock.elapsedTime * 1.2) * 0.03;

    // Mouth open driven by audio volume
    const volume = analyserRef.current
      ? analyserRef.current.getAverageFrequency() / 255
      : 0;
    const targetY = isPlaying ? 0.05 + volume * 0.12 : 0.05;
    mouthRef.current.scale.y = THREE.MathUtils.lerp(mouthRef.current.scale.y, targetY * 10, 0.2);
  });

  return (
    <group>
      {/* Head */}
      <mesh ref={headRef}>
        <sphereGeometry args={[0.38, 32, 32]} />
        <meshStandardMaterial color="#f5c5a3" />
      </mesh>

      {/* Eyes */}
      {([-0.13, 0.13] as number[]).map((x, i) => (
        <mesh key={i} position={[x, 0.1, 0.36]}>
          <sphereGeometry args={[0.055, 16, 16]} />
          <meshStandardMaterial color="#1a1a2e" />
        </mesh>
      ))}

      {/* Mouth */}
      <mesh ref={mouthRef} position={[0, -0.13, 0.37]} scale={[1, 0.5, 1]}>
        <capsuleGeometry args={[0.055, 0.1, 8, 16]} />
        <meshStandardMaterial color="#c0392b" />
      </mesh>
    </group>
  );
}

export const InteractiveAvatar: React.FC<AvatarProps> = ({ audioElement, isPlaying }) => (
  <div style={{
    width: '260px', height: '260px', borderRadius: '50%',
    overflow: 'hidden', border: '3px solid #10b981',
    boxShadow: '0 0 20px rgba(16, 185, 129, 0.4)',
  }}>
    <Canvas camera={{ position: [0, 0, 1.2], fov: 38 }}>
      <ambientLight intensity={1.8} />
      <directionalLight position={[1, 3, 2]} intensity={1.5} />
      <pointLight position={[-1, -2, -1]} intensity={0.4} />
      <ProceduralAvatar audioElement={audioElement} isPlaying={isPlaying} />
    </Canvas>
  </div>
);
