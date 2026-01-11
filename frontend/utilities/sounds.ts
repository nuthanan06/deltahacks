import { Audio } from 'expo-av';

/**
 * Sound utility for playing beep sounds
 * Generates simple tones programmatically
 */

let increaseSound: Audio.Sound | null = null;
let decreaseSound: Audio.Sound | null = null;

/**
 * Generate a simple beep tone as a data URI
 */
function generateTone(frequency: number, duration: number): string {
  const sampleRate = 44100;
  const numSamples = Math.floor(sampleRate * duration);
  const samples = new Float32Array(numSamples);
  
  for (let i = 0; i < numSamples; i++) {
    // Generate sine wave with fade in/out
    const t = i / sampleRate;
    const fade = Math.min(1, t * 10, (duration - t) * 10);
    samples[i] = Math.sin(2 * Math.PI * frequency * t) * fade * 0.3;
  }
  
  // Convert to WAV format
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);
  
  // WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, numSamples * 2, true);
  
  // Convert float samples to 16-bit PCM
  for (let i = 0; i < numSamples; i++) {
    const intSample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, intSample * 0x7FFF, true);
  }
  
  // Convert to base64
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return 'data:audio/wav;base64,' + btoa(binary);
}

/**
 * Initialize sound effects
 */
export async function initializeSounds() {
  try {
    await Audio.setAudioModeAsync({
      playsInSilentModeIOS: true,
      allowsRecordingIOS: false,
    });

    // Create increase sound (higher pitch ding - 800Hz)
    increaseSound = new Audio.Sound();
    const increaseBeep = generateTone(800, 0.15);
    await increaseSound.loadAsync({ uri: increaseBeep });

    // Create decrease sound (lower pitch - 400Hz)
    decreaseSound = new Audio.Sound();
    const decreaseBeep = generateTone(400, 0.15);
    await decreaseSound.loadAsync({ uri: decreaseBeep });
  } catch (error) {
    console.log('Error initializing sounds:', error);
  }
}

/**
 * Play increase sound (ding)
 */
export async function playIncreaseSound() {
  try {
    if (increaseSound) {
      await increaseSound.replayAsync();
    }
  } catch (error) {
    // Silently ignore errors
  }
}

/**
 * Play decrease sound (lower pitch)
 */
export async function playDecreaseSound() {
  try {
    if (decreaseSound) {
      await decreaseSound.replayAsync();
    }
  } catch (error) {
    // Silently ignore errors
  }
}

/**
 * Cleanup sounds
 */
export async function cleanupSounds() {
  try {
    if (increaseSound) {
      await increaseSound.unloadAsync();
      increaseSound = null;
    }
    if (decreaseSound) {
      await decreaseSound.unloadAsync();
      decreaseSound = null;
    }
  } catch (error) {
    // Silently ignore errors
  }
}

