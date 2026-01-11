import * as Haptics from 'expo-haptics';
import { Audio } from 'expo-av';

/**
 * Simple sound utility - plays a note when quantity changes
 */

let audioInitialized = false;

/**
 * Initialize audio mode
 */
async function ensureAudioMode() {
  if (!audioInitialized) {
    try {
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        allowsRecordingIOS: false,
      });
      audioInitialized = true;
      console.log('✅ Audio mode initialized');
    } catch (error) {
      console.error('Error setting audio mode:', error);
    }
  }
}

/**
 * Generate a simple beep tone as data URI
 */
function generateBeep(frequency: number, duration: number = 0.2): string {
  const sampleRate = 44100;
  const numSamples = Math.floor(sampleRate * duration);
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);
  
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };
  
  // WAV header
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, numSamples * 2, true);
  
  // Generate sine wave
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const fade = Math.min(1, t * 20, (duration - t) * 20);
    const sample = Math.sin(2 * Math.PI * frequency * t) * fade * 0.5;
    view.setInt16(44 + i * 2, Math.floor(sample * 32767), true);
  }
  
  // Convert to base64
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return `data:audio/wav;base64,${btoa(binary)}`;
}

/**
 * Play a beep sound
 */
async function playBeep(frequency: number) {
  try {
    await ensureAudioMode();
    
    const dataUri = generateBeep(frequency, 0.2);
    const { sound } = await Audio.Sound.createAsync({ uri: dataUri });
    
    await sound.playAsync();
    console.log(`🔊 Playing beep at ${frequency}Hz`);
    
    // Clean up after playing
    sound.setOnPlaybackStatusUpdate((status) => {
      if (status.isLoaded && status.didJustFinish) {
        sound.unloadAsync();
      }
    });
  } catch (error) {
    console.error('Error playing beep:', error);
  }
}

/**
 * Play increase sound (higher pitch note)
 */
export async function playIncreaseSound() {
  try {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    await playBeep(800); // Higher frequency
  } catch (error) {
    console.error('Error playing increase sound:', error);
  }
}

/**
 * Play decrease sound (lower pitch note)
 */
export async function playDecreaseSound() {
  try {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await playBeep(400); // Lower frequency
  } catch (error) {
    console.error('Error playing decrease sound:', error);
  }
}

/**
 * Play a test frequency on app launch
 */
export async function playTestSound() {
  try {
    console.log('🔊 Playing test sound at 600Hz...');
    await playBeep(600);
    console.log('🔊 Test sound should have played');
  } catch (error) {
    console.error('Error playing test sound:', error);
  }
}

/**
 * Initialize sounds
 */
export async function initializeSounds() {
  // Just ensure audio mode is set up
  await ensureAudioMode();
}

/**
 * Cleanup (no-op, but kept for compatibility)
 */
export async function cleanupSounds() {
  // Nothing to cleanup
}

