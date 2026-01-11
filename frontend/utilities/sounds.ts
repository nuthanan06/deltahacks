import * as Haptics from 'expo-haptics';
import { Audio } from 'expo-av';

/**
 * Simple sound utility - plays a note when quantity changes
 */

let audioModeSet = false;

/**
 * Play increase sound (higher pitch note)
 */
export async function playIncreaseSound() {
  try {
    // Haptic feedback
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    
    // Play a simple beep note
    await playBeep(800); // Higher frequency
  } catch (error) {
    // Just haptics if audio fails
  }
}

/**
 * Play decrease sound (lower pitch note)
 */
export async function playDecreaseSound() {
  try {
    // Haptic feedback
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    
    // Play a simple beep note
    await playBeep(400); // Lower frequency
  } catch (error) {
    // Just haptics if audio fails
  }
}

/**
 * Play a simple beep using expo-av
 */
async function playBeep(frequency: number) {
  try {
    if (!audioModeSet) {
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        allowsRecordingIOS: false,
      });
      audioModeSet = true;
    }

    // Create a very short audio clip
    const duration = 0.1; // 100ms
    const sampleRate = 44100;
    const numSamples = Math.floor(sampleRate * duration);
    
    // Generate simple sine wave
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
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
    
    // Generate tone
    for (let i = 0; i < numSamples; i++) {
      const t = i / sampleRate;
      const fade = Math.min(1, t * 100, (duration - t) * 100);
      const sample = Math.sin(2 * Math.PI * frequency * t) * fade * 0.3;
      view.setInt16(44 + i * 2, Math.floor(sample * 32767), true);
    }
    
    // Convert to base64
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    const dataUri = `data:audio/wav;base64,${base64}`;
    
    // Play the sound
    const { sound } = await Audio.Sound.createAsync({ uri: dataUri });
    await sound.playAsync();
    
    // Clean up after playing
    sound.setOnPlaybackStatusUpdate((status) => {
      if (status.isLoaded && status.didJustFinish) {
        sound.unloadAsync();
      }
    });
  } catch (error) {
    // Silently fail - haptics will still work
  }
}

/**
 * Initialize sounds (no-op, but kept for compatibility)
 */
export async function initializeSounds() {
  // Haptics don't need initialization
}

/**
 * Cleanup (no-op, but kept for compatibility)
 */
export async function cleanupSounds() {
  // Nothing to cleanup
}

