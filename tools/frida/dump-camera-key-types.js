'use strict';

/*
 * Read-only Camera2 key/type tracer for Nothing Camera.
 *
 * Purpose:
 * - enumerate public CameraCharacteristics, request, result, session and physical-request keys;
 * - recover Java generic types from CameraMetadataNative.Key where reflection permits;
 * - log the exact type/value used by stock Builder.set() and session parameters;
 * - never mutate requests, permissions, camera IDs or application state.
 *
 * Run on an authorized test device:
 *   frida -U -f com.nothing.camera \
 *     -l tools/frida/dump-camera-key-types.js \
 *     -o traces/key-types.log
 */

const CONFIG = {
  onlyVendorKeys: true,
  includeCharacteristicValues: true,
  maxArrayItems: 128,
  maxStringLength: 1200,
};

function emit(kind, payload) {
  send(Object.assign({
    schema: 1,
    source: 'dump-camera-key-types',
    kind,
    timestampMs: Date.now(),
    pid: Process.id,
    tid: Process.getCurrentThreadId(),
  }, payload || {}));
}

function truncate(value) {
  const text = String(value);
  if (text.length <= CONFIG.maxStringLength) return text;
  return text.slice(0, CONFIG.maxStringLength) + `…<${text.length - CONFIG.maxStringLength} chars>`;
}

setImmediate(function () {
  Java.perform(function () {
    const ActivityThread = Java.use('android.app.ActivityThread');
    const CameraManager = Java.use('android.hardware.camera2.CameraManager');
    const CaptureRequestBuilder = Java.use('android.hardware.camera2.CaptureRequest$Builder');
    const SessionConfiguration = Java.use('android.hardware.camera2.params.SessionConfiguration');
    const ReflectArray = Java.use('java.lang.reflect.Array');

    function className(value) {
      if (value === null || value === undefined) return null;
      try {
        return value.getClass().getName().toString();
      } catch (_) {
        return typeof value;
      }
    }

    function summarize(value, depth) {
      const level = depth || 0;
      if (value === null || value === undefined) return null;
      if (level > 4) return `<${className(value)}>`;

      try {
        const type = className(value);
        if (
          type === 'java.lang.String' ||
          type === 'java.lang.Integer' ||
          type === 'java.lang.Long' ||
          type === 'java.lang.Float' ||
          type === 'java.lang.Double' ||
          type === 'java.lang.Boolean' ||
          type === 'java.lang.Byte' ||
          type === 'java.lang.Short' ||
          type === 'java.math.BigInteger'
        ) {
          return { javaClass: type, value: truncate(value.toString()) };
        }

        if (type && type.startsWith('[')) {
          const length = ReflectArray.getLength(value);
          const values = [];
          const limit = Math.min(length, CONFIG.maxArrayItems);
          for (let index = 0; index < limit; index += 1) {
            values.push(summarize(ReflectArray.get(value, index), level + 1));
          }
          if (length > limit) values.push(`<${length - limit} more>`);
          return { javaClass: type, length, values };
        }

        try {
          if (value.iterator) {
            const iterator = value.iterator();
            const values = [];
            while (iterator.hasNext() && values.length < CONFIG.maxArrayItems) {
              values.push(summarize(iterator.next(), level + 1));
            }
            if (iterator.hasNext()) values.push('<more>');
            return { javaClass: type, values };
          }
        } catch (_) {}

        return { javaClass: type, value: truncate(value.toString()) };
      } catch (error) {
        return { error: String(error), javaClass: className(value) };
      }
    }

    function keyName(key) {
      try {
        return key.getName().toString();
      } catch (_) {
        return truncate(key);
      }
    }

    function shouldInclude(name) {
      if (!CONFIG.onlyVendorKeys) return true;
      return name.startsWith('com.') || name.startsWith('org.') || name.startsWith('vendor.');
    }

    function reflectMember(object, names) {
      if (!object) return null;
      const clazz = object.getClass();

      for (const name of names) {
        try {
          const method = clazz.getDeclaredMethod(name, []);
          method.setAccessible(true);
          return method.invoke(object, []);
        } catch (_) {}
      }

      for (const name of names) {
        try {
          const field = clazz.getDeclaredField(name);
          field.setAccessible(true);
          return field.get(object);
        } catch (_) {}
      }

      return null;
    }

    function typeNameFromTypeReference(typeReference) {
      if (!typeReference) return null;
      try {
        const type = typeReference.getType();
        if (type) return type.getTypeName().toString();
      } catch (_) {}
      try {
        return typeReference.toString();
      } catch (_) {
        return null;
      }
    }

    function inspectKey(key) {
      const name = keyName(key);
      const nativeKey = reflectMember(key, ['getNativeKey', 'mKey']);
      const typeReference = reflectMember(nativeKey || key, ['getTypeReference', 'mTypeReference']);
      const vendorId = reflectMember(nativeKey || key, ['getVendorId', 'mVendorId']);
      const nativeType = reflectMember(nativeKey || key, ['getNativeType', 'mNativeType']);
      const tag = reflectMember(nativeKey || key, ['getTag', 'mTag']);

      return {
        name,
        keyJavaClass: className(key),
        nativeKeyJavaClass: className(nativeKey),
        javaType: typeNameFromTypeReference(typeReference),
        vendorId: summarize(vendorId, 0),
        nativeType: summarize(nativeType, 0),
        tag: summarize(tag, 0),
      };
    }

    function toArray(listLike) {
      const values = [];
      if (!listLike) return values;
      try {
        const iterator = listLike.iterator();
        while (iterator.hasNext()) values.push(iterator.next());
        return values;
      } catch (_) {}
      try {
        const length = ReflectArray.getLength(listLike);
        for (let index = 0; index < length; index += 1) {
          values.push(ReflectArray.get(listLike, index));
        }
      } catch (_) {}
      return values;
    }

    function emitKeySet(cameraId, domain, keys, characteristics) {
      toArray(keys).forEach(function (key) {
        const metadata = inspectKey(key);
        if (!shouldInclude(metadata.name)) return;

        let value = null;
        let valueError = null;
        if (domain === 'characteristic' && CONFIG.includeCharacteristicValues) {
          try {
            value = summarize(characteristics.get(key), 0);
          } catch (error) {
            valueError = String(error);
          }
        }

        emit('key-definition', {
          cameraId,
          domain,
          key: metadata,
          value,
          valueError,
        });
      });
    }

    function enumerateCamera(cameraManager, cameraId) {
      try {
        const characteristics = cameraManager.getCameraCharacteristics(cameraId);
        emit('camera-start', {
          cameraId,
          physicalCameraIds: summarize(characteristics.getPhysicalCameraIds(), 0),
        });

        emitKeySet(cameraId, 'characteristic', characteristics.getKeys(), characteristics);
        emitKeySet(cameraId, 'request', characteristics.getAvailableCaptureRequestKeys(), characteristics);
        emitKeySet(cameraId, 'result', characteristics.getAvailableCaptureResultKeys(), characteristics);

        try {
          emitKeySet(cameraId, 'session', characteristics.getAvailableSessionKeys(), characteristics);
        } catch (error) {
          emit('domain-unavailable', { cameraId, domain: 'session', error: String(error) });
        }

        try {
          emitKeySet(
            cameraId,
            'physical-request',
            characteristics.getAvailablePhysicalCameraRequestKeys(),
            characteristics
          );
        } catch (error) {
          emit('domain-unavailable', { cameraId, domain: 'physical-request', error: String(error) });
        }

        emit('camera-complete', { cameraId });
      } catch (error) {
        emit('camera-error', { cameraId, error: String(error) });
      }
    }

    function enumeratePublicCameras() {
      try {
        const application = ActivityThread.currentApplication();
        if (!application) throw new Error('currentApplication() returned null');
        const context = application.getApplicationContext();
        const manager = Java.cast(
          context.getSystemService('camera'),
          CameraManager
        );
        const ids = manager.getCameraIdList();
        for (let index = 0; index < ids.length; index += 1) {
          enumerateCamera(manager, ids[index].toString());
        }
        emit('enumeration-complete', { cameraIds: summarize(ids, 0) });
      } catch (error) {
        emit('enumeration-error', { error: String(error) });
      }
    }

    function installAllOverloads(clazz, methodName, callback) {
      if (!clazz[methodName]) {
        emit('hook-unavailable', { className: clazz.$className, methodName });
        return;
      }
      clazz[methodName].overloads.forEach(function (overload) {
        const signature = overload.argumentTypes.map((type) => type.className).join(',');
        overload.implementation = function () {
          const args = Array.prototype.slice.call(arguments);
          try {
            callback.call(this, args, signature);
          } catch (error) {
            emit('hook-observer-error', {
              className: clazz.$className,
              methodName,
              signature,
              error: String(error),
            });
          }
          return overload.apply(this, args);
        };
        emit('hook-installed', { className: clazz.$className, methodName, signature });
      });
    }

    installAllOverloads(CaptureRequestBuilder, 'set', function (args, signature) {
      const metadata = inspectKey(args[0]);
      if (!shouldInclude(metadata.name)) return;
      emit('builder-set', {
        signature,
        key: metadata,
        value: summarize(args[1], 0),
      });
    });

    installAllOverloads(CaptureRequestBuilder, 'setPhysicalCameraKey', function (args, signature) {
      const metadata = inspectKey(args[0]);
      emit('builder-set-physical-key', {
        signature,
        key: metadata,
        value: summarize(args[1], 0),
        physicalCameraId: args[2] === null ? null : String(args[2]),
      });
    });

    installAllOverloads(SessionConfiguration, 'setSessionParameters', function (args, signature) {
      const request = args[0];
      const values = [];
      try {
        const iterator = request.getKeys().iterator();
        while (iterator.hasNext()) {
          const key = iterator.next();
          const metadata = inspectKey(key);
          if (!shouldInclude(metadata.name)) continue;
          values.push({ key: metadata, value: summarize(request.get(key), 0) });
        }
      } catch (error) {
        values.push({ error: String(error) });
      }
      emit('session-parameters', { signature, values });
    });

    emit('hooks-ready', {
      processName: ActivityThread.currentProcessName().toString(),
      onlyVendorKeys: CONFIG.onlyVendorKeys,
    });

    // Delay enumeration until the application has completed initial attachment.
    Java.scheduleOnMainThread(function () {
      enumeratePublicCameras();
    });
  });
});
