// Pages Advanced Mode entry. The host is compiled from the selected public origin.
import worker from './worker.mjs';
export default {
  fetch(request, env, context) {
    return worker.fetch(request, {
      ...env,
      MISEPORT_ALLOWED_HOSTS: __MISEPORT_HOST__,
      MISEPORT_ALLOWED_ORIGINS: 'https://muse.ai'
    }, context);
  }
};
