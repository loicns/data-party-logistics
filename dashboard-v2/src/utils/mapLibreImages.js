const TRANSPARENT_PIXEL = {
  width: 1,
  height: 1,
  data: new Uint8Array([0, 0, 0, 0]),
};

export function installTransparentMissingImageHandler(map) {
  map.on('styleimagemissing', ({ id }) => {
    if (!id || map.hasImage(id)) return;

    try {
      map.addImage(id, TRANSPARENT_PIXEL);
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn(
          `Could not register fallback map image "${id}": ${
            error instanceof Error ? error.message : String(error)
          }`
        );
      }
    }
  });
}
