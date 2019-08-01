# header

![fmt](img/wav-sound-format.gif)

## ChunkID

Contains the letters "RIFF" in ASCII form

## ChunkSize

36 + SubChunk2Size, or more precisely:

4 + (8 + SubChunk1Size) + (8 + SubChunk2Size)

This is the size of the rest of the chunk following this number.  This is the size of the entire file in bytes minus 8 bytes for the two fields not included in this count:
ChunkID and ChunkSize.

## Format

Contains the letters "WAVE"

## Subchunk1ID

Contains the letters "fmt "

## Subchunk1Size

16 for PCM.  This is the size of the rest of the Subchunk which follows this number.

## AudioFormat

PCM = 1. Values other than 1 indicate some form of compression.

## NumChannels

Mono = 1, Stereo = 2, etc

## SampleRate

8000, 44100, etc.

## ByteRate

== SampleRate * NumChannels * BitsPerSample/8

## BlockAlign

 == NumChannels * BitsPerSample/8

## BitsPerSample

8 bits = 8, 16 bits = 16, etc.

## Subchunk2ID 

Contains the letters "data"

## Subchunk2Size    

== NumSamples * NumChannels * BitsPerSample/8

This is the number of bytes in the data.

You can also think of this as the size of the read of the subchunk following this number.