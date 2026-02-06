import 'dart:typed_data';

class AudioUtils {
  /// Converts normalized float audio samples (-1.0 to 1.0) to a valid 16-bit PCM WAV file buffer.
  static Uint8List createWavFile(List<double> samples, int sampleRate) {
    // 1. Convert floats to 16-bit PCM integers
    final pcmData = ByteData(samples.length * 2);
    for (int i = 0; i < samples.length; i++) {
        double s = samples[i];
        // Clamp to -1.0 to 1.0
        if (s > 1.0) s = 1.0;
        if (s < -1.0) s = -1.0;
        
        // Convert to 16-bit int
        int val = (s * 32767).round();
        pcmData.setInt16(i * 2, val, Endian.little);
    }

    // 2. Create Header
    final header = _createWavHeader(samples.length * 2, sampleRate);
    
    // 3. Combine
    final wavFile = Uint8List(header.length + pcmData.lengthInBytes);
    wavFile.setRange(0, header.length, header);
    wavFile.setRange(header.length, wavFile.length, pcmData.buffer.asUint8List());
    
    return wavFile;
  }

  static Uint8List _createWavHeader(int dataSize, int sampleRate) {
    final buffer = ByteData(44);
    final channels = 1;
    final bitDepth = 16;
    final byteRate = sampleRate * channels * (bitDepth ~/ 8);
    final blockAlign = channels * (bitDepth ~/ 8);

    // RIFF chunk
    _writeString(buffer, 0, 'RIFF');
    buffer.setUint32(4, 36 + dataSize, Endian.little); // ChunkSize
    _writeString(buffer, 8, 'WAVE');

    // fmt chunk
    _writeString(buffer, 12, 'fmt ');
    buffer.setUint32(16, 16, Endian.little); // Subchunk1Size
    buffer.setUint16(20, 1, Endian.little); // AudioFormat (1 = PCM)
    buffer.setUint16(22, channels, Endian.little);
    buffer.setUint32(24, sampleRate, Endian.little);
    buffer.setUint32(28, byteRate, Endian.little);
    buffer.setUint16(32, blockAlign, Endian.little);
    buffer.setUint16(34, bitDepth, Endian.little);

    // data chunk
    _writeString(buffer, 36, 'data');
    buffer.setUint32(40, dataSize, Endian.little);

    return buffer.buffer.asUint8List();
  }

  static void _writeString(ByteData buffer, int offset, String text) {
    for (int i = 0; i < text.length; i++) {
      buffer.setUint8(offset + i, text.codeUnitAt(i));
    }
  }
}
