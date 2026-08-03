'use strict';

/*
 * Generic Camera2 routing trace for Nothing Camera.
 *
 * Intended for an authorized test device. The script observes camera IDs, session
 * parameters, output physical IDs and capture request metadata. It does not modify
 * requests or bypass Android permissions.
 */

const CONFIG = {
  routingKeysOnly: false,
  includeOpenStacks: true,
  includeSessionStacks: true,
  maxValueLength: 800,
  maxArrayItems: 64,
};

const ROUTING_KEY_PATTERN = new RegExp(
  [
    'zoom',
    'crop',
    'focal',
    'physical',
    'sensorScenario',
    'forceSensorMode',
    'seamless',
    'insensor',
    'remosaic',
    'multicam',
    'cameraFlex',
    'flexibleCapabilities',
    'pipDevices',
    'proprietaryRequest',
    'initrequest',
    'tnrOffByPhysicalIds',
    'nothing\\.camera',
    'sois',
    'supereis',
  ].join('|'),
  'i'
);

function emit(kind, data) {
  const record = Object.assign(
    {
      schema: 1,
      source: 'trace-camera2-routing',
      kind,
      timestampMs: Date.now(),
      pid: Process.id,
      tid: Process.getCurrentThreadId(),
    },
    data || {}
  );
  send(record);
}

function truncate(text) {
  const value = String(text);
  if (value.length <= CONFIG.maxValueLength) return value;
  return value.slice(0, CONFIG.maxValueLength) + `…<${value.length - CONFIG.maxValueLength} chars>`;
}

setImmediate(function () {
  Java.perform(function () {
    const Throwable = Java.use('java.lang.Throwable');
    const Log = Java.use('android.util.Log');
    const JArray = Java.use('java.lang.reflect.Array');

    function stackTrace() {
      try {
        return truncate(Log.getStackTraceString(Throwable.$new()).toString());
      } catch (error) {
        return `<stack-error:${error}>`;
      }
    }

    function className(value) {
      try {
        return value === null || value === undefined
          ? null
          : value.getClass().getName().toString();
      } catch (_) {
        return typeof value;
      }
    }

    function summarize(value, depth) {
      const level = depth || 0;
      if (value === null || value === undefined) return null;
      if (level > 3) return `<${className(value)}>`;

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
          type === 'java.lang.Short'
        ) {
          return truncate(value.toString());
        }

        if (type && type.startsWith('[')) {
          const length = JArray.getLength(value);
          const output = [];
          const limit = Math.min(length, CONFIG.maxArrayItems);
          for (let index = 0; index < limit; index += 1) {
            output.push(summarize(JArray.get(value, index), level + 1));
          }
          if (length > limit) output.push(`<${length - limit} more>`);
          return { type, length, values: output };
        }

        if (type && (type.startsWith('java.util.') || type.startsWith('android.util.Array'))) {
          try {
            const iterator = value.iterator();
            const output = [];
            while (iterator.hasNext() && output.length < CONFIG.maxArrayItems) {
              output.push(summarize(iterator.next(), level + 1));
            }
            if (iterator.hasNext()) output.push('<more>');
            return { type, values: output };
          } catch (_) {
            return { type, value: truncate(value.toString()) };
          }
        }

        return { type, value: truncate(value.toString()) };
      } catch (error) {
        return `<summary-error:${error}>`;
      }
    }

    function firstArrayItem(value) {
      if (value === null || value === undefined) return null;
      try {
        return JArray.getLength(value) > 0 ? JArray.get(value, 0) : null;
      } catch (_) {
        return null;
      }
    }

    function scalarString(value) {
      if (value === null || value === undefined) return null;
      try {
        return value.toString();
      } catch (_) {
        return String(value);
      }
    }

    function cameraKeyName(key) {
      try {
        return key.getName().toString();
      } catch (_) {
        try {
          return key.toString();
        } catch (error) {
          return `<key-error:${error}>`;
        }
      }
    }

    function shouldLogKey(name) {
      return !CONFIG.routingKeysOnly || ROUTING_KEY_PATTERN.test(name);
    }

    function requestSnapshot(request) {
      const output = {};
      if (!request) return output;
      try {
        const keys = request.getKeys();
        const iterator = keys.iterator();
        while (iterator.hasNext()) {
          const key = iterator.next();
          const name = cameraKeyName(key);
          if (!shouldLogKey(name)) continue;
          try {
            output[name] = summarize(request.get(key), 0);
          } catch (error) {
            output[name] = `<get-error:${error}>`;
          }
        }
      } catch (error) {
        output.__snapshotError = String(error);
      }
      return output;
    }

    function hookOverloads(classNameValue, methodName, before, after) {
      let clazz;
      try {
        clazz = Java.use(classNameValue);
      } catch (error) {
        emit('hook-unavailable', { className: classNameValue, methodName, error: String(error) });
        return;
      }

      if (!clazz[methodName]) {
        emit('hook-unavailable', {
          className: classNameValue,
          methodName,
          error: 'method-not-found',
        });
        return;
      }

      clazz[methodName].overloads.forEach(function (overload) {
        const signature = overload.argumentTypes.map((type) => type.className).join(',');
        overload.implementation = function () {
          const args = Array.prototype.slice.call(arguments);
          let context = {};
          try {
            context = before ? before.call(this, args, signature) || {} : {};
          } catch (error) {
            emit('hook-before-error', {
              className: classNameValue,
              methodName,
              signature,
              error: String(error),
            });
          }

          let result;
          let thrown;
          try {
            result = overload.apply(this, args);
          } catch (error) {
            thrown = error;
          }

          try {
            if (after) after.call(this, result, thrown, context, args, signature);
          } catch (error) {
            emit('hook-after-error', {
              className: classNameValue,
              methodName,
              signature,
              error: String(error),
            });
          }

          if (thrown) throw thrown;
          return result;
        };

        emit('hook-installed', { className: classNameValue, methodName, signature });
      });
    }

    // Stock-build-specific hooks derived from the static DEX open path. They are
    // observational only and fail closed with hook-unavailable on other versions.
    hookOverloads(
      'com.nothing.common.setting.SettingContext',
      'setCameraId',
      function (args, signature) {
        emit('nothing-camera-id-set', {
          signature,
          cameraId: args.length > 0 ? scalarString(args[0]) : null,
          stack: CONFIG.includeOpenStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'com.nothing.common.setting.SettingContext',
      'getCameraId',
      function (_args, signature) {
        return { signature };
      },
      function (result, thrown, context) {
        emit('nothing-camera-id-get', {
          signature: context.signature,
          cameraId: thrown ? null : scalarString(result),
          error: thrown ? String(thrown) : null,
        });
      }
    );

    [
      'getFirstBackCameraId',
      'getFirstBackLogicCameraId',
      'getWideAngleCameraId',
      'getTeleCameraId',
      'getSatCameraId',
    ].forEach(function (methodName) {
      hookOverloads(
        'com.nothing.common.setting.CameraDeviceInfoManager',
        methodName,
        function (_args, signature) {
          return { signature };
        },
        function (result, thrown, context) {
          emit('nothing-camera-id-helper', {
            methodName,
            signature: context.signature,
            cameraId: thrown ? null : scalarString(result),
            error: thrown ? String(thrown) : null,
          });
        }
      );
    });

    ['openCameraAsync', 'resumeCameraAsync'].forEach(function (methodName) {
      hookOverloads(
        'com.nothing.cameracore.context.module.ModuleContext',
        methodName,
        function (args, signature) {
          emit('nothing-module-open-request', {
            methodName,
            signature,
            cameraId: args.length > 0 ? scalarString(args[0]) : null,
            stack: CONFIG.includeOpenStacks ? stackTrace() : null,
          });
          return {};
        }
      );
    });

    hookOverloads(
      'com.nothing.cameracore.context.module.CameraContext',
      'openCamera',
      function (args, signature) {
        emit('nothing-camera-context-open', {
          signature,
          cameraId: args.length > 0 ? scalarString(args[0]) : null,
          args: args.map((value) => summarize(value, 0)),
          stack: CONFIG.includeOpenStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'com.nothing.cameracore.context.module.CameraContext$3',
      'execute',
      function (args, signature) {
        const commandArgs = args.length > 0 ? args[0] : null;
        const cameraId = firstArrayItem(commandArgs);
        emit('nothing-open-dispatch', {
          signature,
          cameraId: scalarString(cameraId),
          commandArgs: summarize(commandArgs, 0),
          stack: CONFIG.includeOpenStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'android.hardware.camera2.CameraManager',
      'getCameraIdList',
      function () {
        return {};
      },
      function (result, thrown, _context, _args, signature) {
        emit('camera-id-list', {
          signature,
          result: thrown ? null : summarize(result, 0),
          error: thrown ? String(thrown) : null,
        });
      }
    );

    hookOverloads(
      'android.hardware.camera2.CameraManager',
      'getCameraCharacteristics',
      function (args, signature) {
        return { cameraId: String(args[0]), signature };
      },
      function (result, thrown, context) {
        const physicalIds = [];
        if (!thrown && result) {
          try {
            const iterator = result.getPhysicalCameraIds().iterator();
            while (iterator.hasNext()) physicalIds.push(iterator.next().toString());
          } catch (_) {}
        }
        emit('get-characteristics', {
          cameraId: context.cameraId,
          signature: context.signature,
          physicalIds,
          error: thrown ? String(thrown) : null,
        });
      }
    );

    hookOverloads(
      'android.hardware.camera2.CameraManager',
      'openCamera',
      function (args, signature) {
        const cameraId = args.length > 0 ? String(args[0]) : '<missing>';
        emit('open-camera', {
          cameraId,
          signature,
          args: args.map((value) => summarize(value, 0)),
          stack: CONFIG.includeOpenStacks ? stackTrace() : null,
        });
        return { cameraId, signature };
      },
      function (_result, thrown, context) {
        if (thrown) {
          emit('open-camera-error', {
            cameraId: context.cameraId,
            signature: context.signature,
            error: String(thrown),
          });
        }
      }
    );

    hookOverloads(
      'android.hardware.camera2.params.OutputConfiguration',
      'setPhysicalCameraId',
      function (args, signature) {
        emit('set-output-physical-id', {
          signature,
          physicalCameraId: args[0] === null ? null : String(args[0]),
          outputConfiguration: summarize(this, 0),
          stack: CONFIG.includeSessionStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'android.hardware.camera2.params.SessionConfiguration',
      'setSessionParameters',
      function (args, signature) {
        emit('set-session-parameters', {
          signature,
          request: requestSnapshot(args[0]),
          stack: CONFIG.includeSessionStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'android.hardware.camera2.CaptureRequest$Builder',
      'set',
      function (args, signature) {
        const name = cameraKeyName(args[0]);
        if (shouldLogKey(name)) {
          emit('builder-set', {
            signature,
            key: name,
            value: summarize(args[1], 0),
          });
        }
        return {};
      }
    );

    hookOverloads(
      'android.hardware.camera2.CaptureRequest$Builder',
      'setPhysicalCameraKey',
      function (args, signature) {
        emit('builder-set-physical-key', {
          signature,
          key: cameraKeyName(args[0]),
          value: summarize(args[1], 0),
          physicalCameraId: args[2] === null ? null : String(args[2]),
          stack: CONFIG.includeSessionStacks ? stackTrace() : null,
        });
        return {};
      }
    );

    hookOverloads(
      'android.hardware.camera2.CaptureRequest$Builder',
      'build',
      function (_args, signature) {
        return { signature };
      },
      function (result, thrown, context) {
        emit('builder-build', {
          signature: context.signature,
          request: thrown ? null : requestSnapshot(result),
          error: thrown ? String(thrown) : null,
        });
      }
    );

    [
      'createCaptureSession',
      'createReprocessableCaptureSession',
      'createConstrainedHighSpeedCaptureSession',
      'createCustomCaptureSession',
    ].forEach(function (methodName) {
      hookOverloads(
        'android.hardware.camera2.impl.CameraDeviceImpl',
        methodName,
        function (args, signature) {
          emit('create-session', {
            methodName,
            signature,
            args: args.map((value) => summarize(value, 0)),
            stack: CONFIG.includeSessionStacks ? stackTrace() : null,
          });
          return {};
        }
      );
    });

    [
      'capture',
      'captureSingleRequest',
      'captureBurst',
      'captureBurstRequests',
      'setRepeatingRequest',
      'setSingleRepeatingRequest',
      'setRepeatingBurst',
      'setRepeatingBurstRequests',
    ].forEach(function (methodName) {
      hookOverloads(
        'android.hardware.camera2.impl.CameraCaptureSessionImpl',
        methodName,
        function (args, signature) {
          const requests = [];
          if (args.length > 0 && args[0]) {
            try {
              const type = className(args[0]);
              if (type && type.startsWith('java.util.')) {
                const iterator = args[0].iterator();
                while (iterator.hasNext() && requests.length < CONFIG.maxArrayItems) {
                  requests.push(requestSnapshot(iterator.next()));
                }
              } else {
                requests.push(requestSnapshot(args[0]));
              }
            } catch (error) {
              requests.push({ __captureSnapshotError: String(error) });
            }
          }
          emit('submit-request', { methodName, signature, requests });
          return {};
        }
      );
    });

    emit('java-hooks-ready', {
      routingKeysOnly: CONFIG.routingKeysOnly,
      processName: Java.use('android.app.ActivityThread').currentProcessName().toString(),
    });
  });

  // Optional NDK observation. The stock app may not use these symbols, and absence is normal.
  try {
    const lookup = Module.findGlobalExportByName
      ? Module.findGlobalExportByName.bind(Module)
      : function (name) {
          return Module.findExportByName(null, name);
        };
    const openCamera = lookup('ACameraManager_openCamera');
    if (openCamera) {
      Interceptor.attach(openCamera, {
        onEnter(args) {
          this.cameraId = args[1].isNull() ? null : args[1].readUtf8String();
          emit('ndk-open-camera', { cameraId: this.cameraId, address: String(openCamera) });
        },
        onLeave(retval) {
          emit('ndk-open-camera-return', {
            cameraId: this.cameraId,
            status: retval.toInt32(),
          });
        },
      });
      emit('native-hook-installed', { symbol: 'ACameraManager_openCamera', address: String(openCamera) });
    } else {
      emit('native-hook-unavailable', { symbol: 'ACameraManager_openCamera' });
    }
  } catch (error) {
    emit('native-hook-error', { symbol: 'ACameraManager_openCamera', error: String(error) });
  }
});
