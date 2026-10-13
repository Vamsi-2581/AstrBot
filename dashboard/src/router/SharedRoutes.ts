const SharedRoutes = {
  path: '/share',
  component: () => import('@/layouts/blank/BlankLayout.vue'),
  meta: {
    requiresAuth: false,
  },
  children: [
    {
      name: 'SharedConversation',
      path: '/share/:token',
      component: () => import('@/views/share/SharedConversationPage.vue'),
    },
  ],
};

export default SharedRoutes;
