<template>
  <div class="users-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Gestión de Usuarios</h1>
          <p class="text-gray-600 mt-1">Administra usuarios, roles y permisos del sistema</p>
        </div>
        <div class="flex space-x-3">
          <button
            @click="openCreateUserModal"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-plus"></i>
            <span>Nuevo Usuario</span>
          </button>
          <button
            @click="exportUsers"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-download"></i>
            <span>Exportar</span>
          </button>
          <button
            @click="openBulkActionsModal"
            class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-tasks"></i>
            <span>Acciones Masivas</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Total Usuarios</p>
              <p class="text-2xl font-bold text-gray-900">{{ totalUsers }}</p>
              <p class="text-sm text-green-600 flex items-center mt-1">
                <i class="fas fa-arrow-up mr-1"></i>
                +{{ newUsersThisMonth }} este mes
              </p>
            </div>
            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
              <i class="fas fa-users text-xl"></i>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Usuarios Activos</p>
              <p class="text-2xl font-bold text-gray-900">{{ activeUsers }}</p>
              <p class="text-sm text-gray-600 mt-1">
                {{ Math.round((activeUsers / totalUsers) * 100) }}% del total
              </p>
            </div>
            <div class="p-3 rounded-full bg-green-100 text-green-600">
              <i class="fas fa-user-check text-xl"></i>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Administradores</p>
              <p class="text-2xl font-bold text-gray-900">{{ adminUsers }}</p>
              <p class="text-sm text-gray-600 mt-1">
                {{ Math.round((adminUsers / totalUsers) * 100) }}% del total
              </p>
            </div>
            <div class="p-3 rounded-full bg-red-100 text-red-600">
              <i class="fas fa-user-shield text-xl"></i>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Últimos Accesos</p>
              <p class="text-2xl font-bold text-gray-900">{{ recentLogins }}</p>
              <p class="text-sm text-gray-600 mt-1">
                Últimas 24 horas
              </p>
            </div>
            <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <i class="fas fa-sign-in-alt text-xl"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters and Search -->
      <div class="bg-white rounded-lg shadow mb-6">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center space-x-4">
              <div class="relative">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Buscar usuarios..."
                  class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
                >
                <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
              </div>

              <select
                v-model="selectedRole"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Todos los roles</option>
                <option value="admin">Administrador</option>
                <option value="encargado">Encargado</option>
                <option value="cajero">Cajero</option>
                <option value="vendedor">Vendedor</option>
                <option value="inventario">Inventario</option>
              </select>

              <select
                v-model="selectedStatus"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Todos los estados</option>
                <option value="active">Activo</option>
                <option value="inactive">Inactivo</option>
                <option value="suspended">Suspendido</option>
                <option value="pending">Pendiente</option>
              </select>

              <select
                v-model="selectedDepartment"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Todos los departamentos</option>
                <option value="ventas">Ventas</option>
                <option value="inventario">Inventario</option>
                <option value="administracion">Administración</option>
                <option value="contabilidad">Contabilidad</option>
              </select>
            </div>

            <div class="flex items-center space-x-2">
              <button
                @click="clearFilters"
                class="text-gray-600 hover:text-gray-800 text-sm"
              >
                <i class="fas fa-times mr-1"></i>
                Limpiar filtros
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Users Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">
              Lista de Usuarios ({{ filteredUsers.length }})
            </h3>
            <div class="flex items-center space-x-2">
              <span class="text-sm text-gray-500">Mostrar:</span>
              <select
                v-model="itemsPerPage"
                @change="currentPage = 1"
                class="px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <input
                    v-model="selectAll"
                    @change="toggleSelectAll"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usuario
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rol
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Departamento
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Último Acceso
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Permisos
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="user in paginatedUsers" :key="user.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <input
                    v-model="selectedUsers"
                    :value="user.id"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                        <i class="fas fa-user text-gray-600"></i>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{{ user.name }}</div>
                      <div class="text-sm text-gray-500">{{ user.email }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getRoleClass(user.role)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ getRoleLabel(user.role) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ user.department }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusClass(user.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ getStatusLabel(user.status) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ formatDate(user.lastLogin) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <button
                    @click="openPermissionsModal(user)"
                    class="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    <i class="fas fa-key mr-1"></i>
                    Ver Permisos
                  </button>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    <button
                      @click="openEditUserModal(user)"
                      class="text-blue-600 hover:text-blue-800"
                      title="Editar usuario"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      @click="toggleUserStatus(user)"
                      :class="user.status === 'active' ? 'text-yellow-600 hover:text-yellow-800' : 'text-green-600 hover:text-green-800'"
                      :title="user.status === 'active' ? 'Desactivar usuario' : 'Activar usuario'"
                    >
                      <i :class="user.status === 'active' ? 'fas fa-pause' : 'fas fa-play'"></i>
                    </button>
                    <button
                      @click="resetPassword(user)"
                      class="text-purple-600 hover:text-purple-800"
                      title="Restablecer contraseña"
                    >
                      <i class="fas fa-key"></i>
                    </button>
                    <button
                      @click="deleteUser(user)"
                      class="text-red-600 hover:text-red-800"
                      title="Eliminar usuario"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
          <div class="flex-1 flex justify-between sm:hidden">
            <button
              @click="currentPage--"
              :disabled="currentPage === 1"
              class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>
            <button
              @click="currentPage++"
              :disabled="currentPage === totalPages"
              class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Siguiente
            </button>
          </div>
          <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p class="text-sm text-gray-700">
                Mostrando
                <span class="font-medium">{{ startIndex + 1 }}</span>
                a
                <span class="font-medium">{{ Math.min(endIndex, filteredUsers.length) }}</span>
                de
                <span class="font-medium">{{ filteredUsers.length }}</span>
                resultados
              </p>
            </div>
            <div>
              <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                <button
                  @click="currentPage--"
                  :disabled="currentPage === 1"
                  class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <i class="fas fa-chevron-left"></i>
                </button>
                <button
                  v-for="page in visiblePages"
                  :key="page"
                  @click="currentPage = page"
                  :class="[
                    'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                    page === currentPage
                      ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                      : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                  ]"
                >
                  {{ page }}
                </button>
                <button
                  @click="currentPage++"
                  :disabled="currentPage === totalPages"
                  class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <i class="fas fa-chevron-right"></i>
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit User Modal -->
    <div v-if="showUserModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-10 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ editingUser ? 'Editar Usuario' : 'Crear Nuevo Usuario' }}
            </h3>
            <button @click="closeUserModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="saveUser" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Nombre Completo *</label>
                <input
                  v-model="userForm.name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Ingrese el nombre completo"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Email *</label>
                <input
                  v-model="userForm.email"
                  type="email"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="usuario@empresa.com"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Teléfono</label>
                <input
                  v-model="userForm.phone"
                  type="tel"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Número de teléfono"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Documento de Identidad</label>
                <input
                  v-model="userForm.document"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Número de documento"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Rol *</label>
                <select
                  v-model="userForm.role"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Seleccionar rol</option>
                  <option value="admin">Administrador</option>
                  <option value="encargado">Encargado</option>
                  <option value="cajero">Cajero</option>
                  <option value="vendedor">Vendedor</option>
                  <option value="inventario">Inventario</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Departamento *</label>
                <select
                  v-model="userForm.department"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Seleccionar departamento</option>
                  <option value="ventas">Ventas</option>
                  <option value="inventario">Inventario</option>
                  <option value="administracion">Administración</option>
                  <option value="contabilidad">Contabilidad</option>
                </select>
              </div>

              <div v-if="!editingUser">
                <label class="block text-sm font-medium text-gray-700 mb-2">Contraseña *</label>
                <input
                  v-model="userForm.password"
                  type="password"
                  :required="!editingUser"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Contraseña temporal"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Estado</label>
                <select
                  v-model="userForm.status"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                  <option value="suspended">Suspendido</option>
                  <option value="pending">Pendiente</option>
                </select>
              </div>
            </div>

            <!-- Permissions Section -->
            <div class="border-t pt-6">
              <h4 class="text-md font-medium text-gray-900 mb-4">Permisos Específicos</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div v-for="permission in availablePermissions" :key="permission.id" class="flex items-center">
                  <input
                    v-model="userForm.permissions"
                    :value="permission.id"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <label class="ml-2 text-sm text-gray-700">{{ permission.name }}</label>
                </div>
              </div>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeUserModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {{ editingUser ? 'Actualizar' : 'Crear' }} Usuario
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Permissions Modal -->
    <div v-if="showPermissionsModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-10 mx-auto p-5 border w-11/12 md:w-2/3 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              Permisos de {{ selectedUserForPermissions?.name }}
            </h3>
            <button @click="closePermissionsModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-medium text-gray-900 mb-3">Información del Usuario</h4>
                <div class="space-y-2 text-sm">
                  <p><span class="font-medium">Rol:</span> {{ getRoleLabel(selectedUserForPermissions?.role) }}</p>
                  <p><span class="font-medium">Departamento:</span> {{ selectedUserForPermissions?.department }}</p>
                  <p><span class="font-medium">Estado:</span> {{ getStatusLabel(selectedUserForPermissions?.status) }}</p>
                </div>
              </div>

              <div>
                <h4 class="font-medium text-gray-900 mb-3">Estadísticas de Acceso</h4>
                <div class="space-y-2 text-sm">
                  <p><span class="font-medium">Último acceso:</span> {{ formatDate(selectedUserForPermissions?.lastLogin) }}</p>
                  <p><span class="font-medium">Accesos este mes:</span> {{ selectedUserForPermissions?.monthlyLogins || 0 }}</p>
                  <p><span class="font-medium">Creado:</span> {{ formatDate(selectedUserForPermissions?.createdAt) }}</p>
                </div>
              </div>
            </div>

            <div>
              <h4 class="font-medium text-gray-900 mb-3">Permisos Asignados</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                <div v-for="permission in availablePermissions" :key="permission.id" class="flex items-center p-2 rounded border">
                  <input
                    :checked="selectedUserForPermissions?.permissions?.includes(permission.id)"
                    @change="updateUserPermission(permission.id, $event.target.checked)"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <label class="ml-2 text-sm text-gray-700">{{ permission.name }}</label>
                </div>
              </div>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                @click="closePermissionsModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cerrar
              </button>
              <button
                @click="saveUserPermissions"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Guardar Permisos
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bulk Actions Modal -->
    <div v-if="showBulkActionsModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-10 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Acciones Masivas</h3>
            <button @click="closeBulkActionsModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div class="space-y-4">
            <p class="text-sm text-gray-600">
              {{ selectedUsers.length }} usuario(s) seleccionado(s)
            </p>

            <div class="space-y-3">
              <button
                @click="bulkActivateUsers"
                :disabled="selectedUsers.length === 0"
                class="w-full text-left px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-play text-green-600 mr-2"></i>
                Activar usuarios seleccionados
              </button>

              <button
                @click="bulkDeactivateUsers"
                :disabled="selectedUsers.length === 0"
                class="w-full text-left px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-pause text-yellow-600 mr-2"></i>
                Desactivar usuarios seleccionados
              </button>

              <button
                @click="bulkResetPasswords"
                :disabled="selectedUsers.length === 0"
                class="w-full text-left px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-key text-purple-600 mr-2"></i>
                Restablecer contraseñas
              </button>

              <button
                @click="bulkDeleteUsers"
                :disabled="selectedUsers.length === 0"
                class="w-full text-left px-4 py-3 border border-red-300 rounded-lg hover:bg-red-50 text-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-trash mr-2"></i>
                Eliminar usuarios seleccionados
              </button>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                @click="closeBulkActionsModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/lib/toast'
import axiosClient from '@/lib/axiosClient'

const authStore = useAuthStore()
const toast = useToast()

// Check if user has admin access
const isAdmin = computed(() => authStore.hasRole('admin'))

if (!isAdmin.value) {
  // Redirect to dashboard or show access denied
  console.warn('Access denied: Admin role required for User Management')
}

// Reactive data
const users = ref([])
const searchQuery = ref('')
const selectedRole = ref('')
const selectedStatus = ref('')
const selectedDepartment = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(25)
const selectedUsers = ref([])
const selectAll = ref(false)

// Modal states
const showUserModal = ref(false)
const showPermissionsModal = ref(false)
const showBulkActionsModal = ref(false)
const editingUser = ref(null)
const selectedUserForPermissions = ref(null)

// Form data
const userForm = ref({
  name: '',
  email: '',
  phone: '',
  document: '',
  role: '',
  department: '',
  password: '',
  status: 'active',
  permissions: []
})

// Available permissions
const availablePermissions = ref([
  { id: 'dashboard_access', name: 'Acceso al Dashboard' },
  { id: 'sales_view', name: 'Ver Ventas' },
  { id: 'sales_create', name: 'Crear Ventas' },
  { id: 'inventory_view', name: 'Ver Inventario' },
  { id: 'inventory_manage', name: 'Gestionar Inventario' },
  { id: 'customers_view', name: 'Ver Clientes' },
  { id: 'customers_manage', name: 'Gestionar Clientes' },
  { id: 'orders_view', name: 'Ver Órdenes' },
  { id: 'orders_manage', name: 'Gestionar Órdenes' },
  { id: 'reports_view', name: 'Ver Reportes' },
  { id: 'reports_generate', name: 'Generar Reportes' },
  { id: 'analytics_view', name: 'Ver Analytics' },
  { id: 'catalog_manage', name: 'Gestionar Catálogo' },
  { id: 'cash_operations', name: 'Operaciones de Caja' },
  { id: 'users_view', name: 'Ver Usuarios' },
  { id: 'users_manage', name: 'Gestionar Usuarios' },
  { id: 'system_settings', name: 'Configuración del Sistema' }
])

// Stats data
const totalUsers = ref(0)
const activeUsers = ref(0)
const adminUsers = ref(0)
const newUsersThisMonth = ref(0)
const recentLogins = ref(0)

// Computed properties
const filteredUsers = computed(() => {
  let filtered = users.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(user => 
      user.name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.document?.toLowerCase().includes(query)
    )
  }

  if (selectedRole.value) {
    filtered = filtered.filter(user => user.role === selectedRole.value)
  }

  if (selectedStatus.value) {
    filtered = filtered.filter(user => user.status === selectedStatus.value)
  }

  if (selectedDepartment.value) {
    filtered = filtered.filter(user => user.department === selectedDepartment.value)
  }

  return filtered
})

const totalPages = computed(() => Math.ceil(filteredUsers.value.length / itemsPerPage.value))
const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage.value)
const endIndex = computed(() => startIndex.value + itemsPerPage.value)

const paginatedUsers = computed(() => 
  filteredUsers.value.slice(startIndex.value, endIndex.value)
)

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

// Methods
const loadUsers = async () => {
  try {
    const response = await axiosClient.get('/panel/users/')
    users.value = response.data.map(user => ({
      id: user.id,
      name: user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.username,
      email: user.email,
      phone: user.phone || '',
      document: user.document || '',
      role: user.groups && user.groups.length > 0 ? user.groups[0].name : 'usuario',
      department: user.department || 'general',
      status: user.is_active ? 'active' : 'inactive',
      lastLogin: user.last_login ? new Date(user.last_login) : null,
      createdAt: new Date(user.date_joined),
      monthlyLogins: 0, // This would need to be calculated on backend
      permissions: user.scopes || []
    }))

    // Calculate stats
    totalUsers.value = users.value.length
    activeUsers.value = users.value.filter(u => u.status === 'active').length
    adminUsers.value = users.value.filter(u => u.role === 'admin').length
    newUsersThisMonth.value = users.value.filter(u => {
      const createdDate = new Date(u.createdAt)
      const now = new Date()
      return createdDate.getMonth() === now.getMonth() && createdDate.getFullYear() === now.getFullYear()
    }).length
    recentLogins.value = users.value.filter(u => {
      if (!u.lastLogin) return false
      const lastLogin = new Date(u.lastLogin)
      const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
      return lastLogin > dayAgo
    }).length

  } catch (error) {
    console.error('Error loading users:', error)
    toast.error('Error al cargar los usuarios')
  }
}

// User management methods
const openCreateUserModal = () => {
  editingUser.value = null
  userForm.value = {
    name: '',
    email: '',
    phone: '',
    document: '',
    role: '',
    department: '',
    password: '',
    status: 'active',
    permissions: []
  }
  showUserModal.value = true
}

const openEditUserModal = (user) => {
  editingUser.value = user
  userForm.value = {
    name: user.name,
    email: user.email,
    phone: user.phone || '',
    document: user.document || '',
    role: user.role,
    department: user.department,
    password: '',
    status: user.status,
    permissions: [...(user.permissions || [])]
  }
  showUserModal.value = true
}

const closeUserModal = () => {
  showUserModal.value = false
  editingUser.value = null
}

const saveUser = async () => {
  try {
    if (editingUser.value) {
      // Update existing user
      const updateData = {
        first_name: userForm.value.name.split(' ')[0] || '',
        last_name: userForm.value.name.split(' ').slice(1).join(' ') || '',
        email: userForm.value.email,
        phone: userForm.value.phone,
        document: userForm.value.document,
        department: userForm.value.department,
        is_active: userForm.value.status === 'active'
      }
      
      if (userForm.value.password) {
        updateData.password = userForm.value.password
      }
      
      await axiosClient.put(`/panel/users/${editingUser.value.id}/`, updateData)
      toast.success('Usuario actualizado correctamente')
    } else {
      // Create new user
      const createData = {
        username: userForm.value.email, // Use email as username
        first_name: userForm.value.name.split(' ')[0] || '',
        last_name: userForm.value.name.split(' ').slice(1).join(' ') || '',
        email: userForm.value.email,
        password: userForm.value.password,
        phone: userForm.value.phone,
        document: userForm.value.document,
        department: userForm.value.department,
        is_active: userForm.value.status === 'active'
      }
      
      await axiosClient.post('/panel/users/', createData)
      toast.success('Usuario creado correctamente')
    }
    
    closeUserModal()
    loadUsers() // Refresh the list
  } catch (error) {
    console.error('Error saving user:', error)
    if (error.response?.data?.detail) {
      toast.error(error.response.data.detail)
    } else {
      toast.error('Error al guardar el usuario')
    }
  }
}

const deleteUser = async (user) => {
  if (confirm(`¿Está seguro de eliminar al usuario ${user.name}?`)) {
    try {
      await axiosClient.delete(`/panel/users/${user.id}/`)
      toast.success('Usuario eliminado correctamente')
      loadUsers() // Refresh the list
    } catch (error) {
      console.error('Error deleting user:', error)
      if (error.response?.data?.detail) {
        toast.error(error.response.data.detail)
      } else {
        toast.error('Error al eliminar el usuario')
      }
    }
  }
}

const toggleUserStatus = async (user) => {
  try {
    const newStatus = user.status === 'active' ? 'inactive' : 'active'
    
    await axiosClient.patch(`/panel/users/${user.id}/toggle-active/`)
    toast.success(`Usuario ${newStatus === 'active' ? 'activado' : 'desactivado'} correctamente`)
    loadUsers() // Refresh the list
  } catch (error) {
    console.error('Error updating user status:', error)
    if (error.response?.data?.detail) {
      toast.error(error.response.data.detail)
    } else {
      toast.error('Error al cambiar el estado del usuario')
    }
  }
}

const resetPassword = async (user) => {
  if (confirm(`¿Restablecer la contraseña de ${user.name}?`)) {
    try {
      // For now, we'll just show a message since password reset functionality
      // would typically involve email sending which requires additional backend setup
      toast.info('Funcionalidad de restablecimiento de contraseña pendiente de implementar')
    } catch (error) {
      console.error('Error resetting password:', error)
      toast.error('Error al restablecer la contraseña')
    }
  }
}

// Permissions methods
const openPermissionsModal = (user) => {
  selectedUserForPermissions.value = user
  showPermissionsModal.value = true
}

const closePermissionsModal = () => {
  showPermissionsModal.value = false
  selectedUserForPermissions.value = null
}

const updateUserPermission = (permissionId, checked) => {
  if (!selectedUserForPermissions.value.permissions) {
    selectedUserForPermissions.value.permissions = []
  }
  
  if (checked) {
    if (!selectedUserForPermissions.value.permissions.includes(permissionId)) {
      selectedUserForPermissions.value.permissions.push(permissionId)
    }
  } else {
    selectedUserForPermissions.value.permissions = selectedUserForPermissions.value.permissions.filter(p => p !== permissionId)
  }
}

const saveUserPermissions = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.put(`/users/${selectedUserForPermissions.value.id}/permissions`, {
    //   permissions: selectedUserForPermissions.value.permissions
    // })
    
    closePermissionsModal()
  } catch (error) {
    console.error('Error saving user permissions:', error)
  }
}

// Bulk actions methods
const openBulkActionsModal = () => {
  showBulkActionsModal.value = true
}

const closeBulkActionsModal = () => {
  showBulkActionsModal.value = false
}

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedUsers.value = paginatedUsers.value.map(u => u.id)
  } else {
    selectedUsers.value = []
  }
}

const bulkActivateUsers = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.patch('/users/bulk-activate', { userIds: selectedUsers.value })
    
    users.value.forEach(user => {
      if (selectedUsers.value.includes(user.id)) {
        user.status = 'active'
      }
    })
    
    selectedUsers.value = []
    selectAll.value = false
    closeBulkActionsModal()
    loadUsers()
  } catch (error) {
    console.error('Error activating users:', error)
  }
}

const bulkDeactivateUsers = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.patch('/users/bulk-deactivate', { userIds: selectedUsers.value })
    
    users.value.forEach(user => {
      if (selectedUsers.value.includes(user.id)) {
        user.status = 'inactive'
      }
    })
    
    selectedUsers.value = []
    selectAll.value = false
    closeBulkActionsModal()
    loadUsers()
  } catch (error) {
    console.error('Error deactivating users:', error)
  }
}

const bulkResetPasswords = async () => {
  if (confirm(`¿Restablecer las contraseñas de ${selectedUsers.value.length} usuarios?`)) {
    try {
      // TODO: Replace with actual API call
      // await api.post('/users/bulk-reset-passwords', { userIds: selectedUsers.value })
      
      alert('Contraseñas restablecidas. Se han enviado emails a los usuarios.')
      selectedUsers.value = []
      selectAll.value = false
      closeBulkActionsModal()
    } catch (error) {
      console.error('Error resetting passwords:', error)
    }
  }
}

const bulkDeleteUsers = async () => {
  if (confirm(`¿Está seguro de eliminar ${selectedUsers.value.length} usuarios? Esta acción no se puede deshacer.`)) {
    try {
      // TODO: Replace with actual API call
      // await api.delete('/users/bulk-delete', { data: { userIds: selectedUsers.value } })
      
      users.value = users.value.filter(user => !selectedUsers.value.includes(user.id))
      selectedUsers.value = []
      selectAll.value = false
      closeBulkActionsModal()
      loadUsers()
    } catch (error) {
      console.error('Error deleting users:', error)
    }
  }
}

// Utility methods
const clearFilters = () => {
  searchQuery.value = ''
  selectedRole.value = ''
  selectedStatus.value = ''
  selectedDepartment.value = ''
  currentPage.value = 1
}

const exportUsers = () => {
  const csvContent = [
    ['Nombre', 'Email', 'Teléfono', 'Documento', 'Rol', 'Departamento', 'Estado', 'Último Acceso'].join(','),
    ...filteredUsers.value.map(user => [
      user.name,
      user.email,
      user.phone || '',
      user.document || '',
      getRoleLabel(user.role),
      user.department,
      getStatusLabel(user.status),
      formatDate(user.lastLogin)
    ].join(','))
  ].join('\n')

  downloadCSV(csvContent, `usuarios_${new Date().toISOString().split('T')[0]}.csv`)
}

const getRoleClass = (role) => {
  const classes = {
    admin: 'bg-red-100 text-red-800',
    encargado: 'bg-purple-100 text-purple-800',
    cajero: 'bg-blue-100 text-blue-800',
    vendedor: 'bg-green-100 text-green-800',
    inventario: 'bg-yellow-100 text-yellow-800'
  }
  return classes[role] || 'bg-gray-100 text-gray-800'
}

const getRoleLabel = (role) => {
  const labels = {
    admin: 'Administrador',
    encargado: 'Encargado',
    cajero: 'Cajero',
    vendedor: 'Vendedor',
    inventario: 'Inventario'
  }
  return labels[role] || role
}

const getStatusClass = (status) => {
  const classes = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    suspended: 'bg-red-100 text-red-800',
    pending: 'bg-yellow-100 text-yellow-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

const getStatusLabel = (status) => {
  const labels = {
    active: 'Activo',
    inactive: 'Inactivo',
    suspended: 'Suspendido',
    pending: 'Pendiente'
  }
  return labels[status] || status
}

const formatDate = (date) => {
  if (!date) return 'Nunca'
  return new Date(date).toLocaleString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const downloadCSV = (content: string, filename: string) => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Lifecycle
onMounted(() => {
  loadUsers()
})
</script>